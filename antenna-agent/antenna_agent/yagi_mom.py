"""Effective-medium wire method-of-moments model of a printed Yagi (NEC2 via PyNEC).

All in-plane PCB dimensions are divided by k (< 1, the wavelength compression of strips on FR4) to get free-space
equivalents; strips become round wires of radius (w/k)/4 (flat-strip equivalence); the ground pour becomes a wire-grid
plate. k is NOT assumed: it is calibrated against the measured directivity of a reference board (see calibrate()).
This is a design-space tool for choosing element lengths/spacings/count. It does not replace the 3D EM solve:
substrate thickness, the balun, and the feed are not in it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

C0 = 299_792_458.0


@dataclass
class Yagi:
    """Lengths in mm (PCB dims). Elements along x, boresight +y. Index 0 = driven, 1.. = directors."""
    L: list[float]            # element lengths, driven first
    W: list[float]            # element widths
    gap: list[float]          # edge-to-edge gaps: [pour->driven, driven->D1, D1->D2, ...]
    Bw: float = 100.0         # pour width (x)
    Lp: float = 36.85         # pour length (y)

    def centres_y(self) -> list[float]:
        y, out = 0.0, []
        for i, (w, g) in enumerate(zip(self.W, self.gap)):
            y += g
            out.append(y + w / 2)
            y += w
        return out


def _wire(g, tag, n, p1, p2, a):
    g.wire(tag, n, *p1, *p2, a, 1.0, 1.0)


def _build(yg: Yagi, k: float, f_mhz: float, cell_frac: float = 0.1, grid: bool = True):
    from PyNEC import nec_context
    s = 1e-3 / k  # mm (PCB) -> m (free-space equivalent)
    nec = nec_context()
    geo = nec.get_geometry()
    lam = C0 / (f_mhz * 1e6)
    tag, feed_tag, feed_seg = 0, None, None
    for i, (Lk, Wk, yc) in enumerate(zip(yg.L, yg.W, yg.centres_y())):
        tag += 1
        nseg = max(11, int(round(Lk * s / (lam / 25))) | 1)  # odd, >= lam/25 resolution -> centre segment exists
        _wire(geo, tag, nseg, (-Lk * s / 2, yc * s, 0.0), (Lk * s / 2, yc * s, 0.0), Wk * s / 4)
        if i == 0:
            feed_tag, feed_seg = tag, nseg // 2 + 1
    if grid:
        X, Y = yg.Bw * s / 2, yg.Lp * s
        nx = max(2, int(math.ceil(2 * X / (cell_frac * lam))))
        ny = max(1, int(math.ceil(Y / (cell_frac * lam))))
        xs, ys = np.linspace(-X, X, nx + 1), np.linspace(-Y, 0.0, ny + 1)
        a_g = (2 * X / nx) / (2 * math.pi)  # equivalent radius of a square wire mesh
        for y in ys:
            for i in range(nx):
                tag += 1
                _wire(geo, tag, 1, (xs[i], y, 0.0), (xs[i + 1], y, 0.0), a_g)
        for x in xs:
            for j in range(ny):
                tag += 1
                _wire(geo, tag, 1, (x, ys[j], 0.0), (x, ys[j + 1], 0.0), a_g)
    nec.geometry_complete(0)
    nec.gn_card(-1, 0, 0, 0, 0, 0, 0, 0)
    nec.ex_card(0, feed_tag, feed_seg, 0, 1.0, 0, 0, 0, 0, 0)
    return nec


def analyze(yg: Yagi, k: float, f_ghz: float, cell_frac: float = 0.1, grid: bool = True, z0: float = 50.0) -> dict:
    """Directivity (dBi, lossless), front/back (dB), boresight direction check, input impedance at f."""
    nec = _build(yg, k, f_ghz * 1e3, cell_frac, grid)
    nec.fr_card(0, 1, f_ghz * 1e3, 0.0)
    nec.rp_card(0, 73, 72, 0, 0, 0, 0, 0.0, 0.0, 2.5, 5.0, 0.0, 0.0)
    rp = nec.get_radiation_pattern(0)
    G = np.array(rp.get_gain())                     # [theta, phi] dBi
    th, ph = np.array(rp.get_theta_angles()), np.array(rp.get_phi_angles())
    i, j = np.unravel_index(np.argmax(G), G.shape)
    # +y boresight is theta = 90, phi = 90 ; -y is phi = 270
    jf, jb = int(np.argmin(abs(ph - 90))), int(np.argmin(abs(ph - 270)))
    it = int(np.argmin(abs(th - 90)))
    Z = complex(nec.get_input_parameters(0).get_impedance()[0])
    gam = (Z - z0) / (Z + z0)
    return dict(f_ghz=f_ghz, gain_dbi=float(G[i, j]), theta=float(th[i]), phi=float(ph[j]),
                fwd_dbi=float(G[it, jf]), back_dbi=float(G[it, jb]), fb_db=float(G[it, jf] - G[it, jb]),
                z=Z, s11_db=float(20 * math.log10(abs(gam))))


def sweep(yg: Yagi, k: float, freqs, **kw) -> list[dict]:
    return [analyze(yg, k, f, **kw) for f in freqs]


# ----------------------------------------------------------------------------- reference board + calibration
def ti_dn034() -> Yagi:
    """TI DN034 as published (mm): driven + 3 directors, ground pour = reflector."""
    return Yagi(L=[44.96, 34.29, 34.29, 34.29], W=[3.05, 3.81, 3.81, 3.81],
                gap=[16.00, 15.49, 15.49, 15.49], Bw=100.0, Lp=36.85)


MEASURED_DIRECTIVITY = {2.40: 7.92, 2.44: 8.62, 2.48: 9.48}   # dBi, DN034 Table 1


def calibrate(ks=np.arange(0.50, 0.901, 0.025), cell_frac=0.1):
    ref = ti_dn034()
    rows = []
    for k in ks:
        d = [analyze(ref, float(k), f, cell_frac=cell_frac)["gain_dbi"] for f in MEASURED_DIRECTIVITY]
        err = np.array(d) - np.array(list(MEASURED_DIRECTIVITY.values()))
        rows.append(dict(k=float(k), model=d, rms=float(np.sqrt(np.mean(err ** 2))), bias=float(err.mean())))
    return rows


def cuts(yg: Yagi, k: float, f_ghz: float, cell_frac: float = 0.1) -> dict:
    """E-plane (xy, theta=90) and H-plane (yz, phi=90) half-power beamwidths and off-axis lobe level (dB below peak)."""
    nec = _build(yg, k, f_ghz * 1e3, cell_frac, True)
    nec.fr_card(0, 1, f_ghz * 1e3, 0.0)
    nec.rp_card(0, 73, 144, 0, 0, 0, 0, 0.0, 0.0, 2.5, 2.5, 0.0, 0.0)
    rp = nec.get_radiation_pattern(0)
    G = np.array(rp.get_gain())
    th, ph = np.array(rp.get_theta_angles()), np.array(rp.get_phi_angles())
    it, jp = int(np.argmin(abs(th - 90))), int(np.argmin(abs(ph - 90)))
    e_ang = (ph - 90 + 180) % 360 - 180      # angle from boresight in the E-plane
    h_ang = th - 90                          # angle from boresight in the H-plane (front half)

    def hpbw(ang, g):
        o = np.argsort(ang); a, v = ang[o], g[o]
        pk = v[np.argmin(abs(a))]
        def edge(sign):
            idx = [i for i in range(len(a)) if sign * a[i] >= 0]
            idx.sort(key=lambda i: sign * a[i])
            for p, q in zip(idx, idx[1:]):
                if v[q] <= pk - 3 < v[p]:
                    return a[p] + (pk - 3 - v[p]) / (v[q] - v[p]) * (a[q] - a[p])
            return float("nan")
        return edge(+1) - edge(-1), pk

    he, pe = hpbw(e_ang, G[it, :])
    hh, ph_ = hpbw(h_ang, G[:, jp])
    far_e = G[it, :][abs(e_ang) > max(2 * he, 60)].max() - pe
    return dict(hpbw_e_deg=float(he), hpbw_h_deg=float(hh), offaxis_e_db=float(far_e), peak_dbi=float(pe))
