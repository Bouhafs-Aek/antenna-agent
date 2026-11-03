"""Matching section from a simulated S11: predict a series line (width Wt, length Lt) at the port that minimises the
worst |S11| over a band. Pure transmission-line post-processing of YOUR HFSS S11 (port plane), Hammerstad microstrip
model; discontinuities and coupling to the radiator are ignored, so treat the result as a starting point for one HFSS run.
"""
from __future__ import annotations

import math

import numpy as np

C0 = 299.792458  # mm * GHz


def microstrip(w_mm: float, h: float, er: float) -> tuple[float, float]:
    """Hammerstad-Jensen (zero thickness): returns (Z0 ohm, eeff)."""
    u = w_mm / h
    a = 1 + math.log((u ** 4 + (u / 52) ** 2) / (u ** 4 + 0.432)) / 49 + math.log(1 + (u / 18.1) ** 3) / 18.7
    b = 0.564 * ((er - 0.9) / (er + 3)) ** 0.053
    ee = (er + 1) / 2 + (er - 1) / 2 * (1 + 10 / u) ** (-a * b)
    f = 6 + (2 * math.pi - 6) * math.exp(-((30.666 / u) ** 0.7528))
    z = 60 * math.log(f / u + math.sqrt(1 + (2 / u) ** 2)) / math.sqrt(ee)
    return z, ee


def width_for_z(z: float, h: float, er: float) -> float:
    lo, hi = 0.05, 12.0
    for _ in range(60):
        mid = (lo + hi) / 2
        (lo, hi) = (mid, hi) if microstrip(mid * h, h, er)[0] > z else (lo, mid)
    return (lo + hi) / 2 * h


def add_line(gamma: np.ndarray, f_ghz: np.ndarray, zt: float, ell_mm: float, ee: float, z0: float = 50.0) -> np.ndarray:
    """Gamma seen at the new port after inserting a lossless line (Zt, ell) between the port and the load."""
    zl = z0 * (1 + gamma) / (1 - gamma)
    th = 2 * np.pi * f_ghz * math.sqrt(ee) * ell_mm / C0
    t = 1j * np.tan(th)
    zin = zt * (zl + zt * t) / (zt + zl * t)
    return (zin - z0) / (zin + z0)


def design(f, gamma, band, h, er, z0=50.0):
    from scipy.optimize import differential_evolution
    m = (f >= band[0]) & (f <= band[1])

    def cost(p):
        zt, ell = p
        ee = microstrip(width_for_z(zt, h, er), h, er)[1]
        g = add_line(gamma[m], f[m], zt, ell, ee, z0)
        return float(np.max(20 * np.log10(np.abs(g) + 1e-9)))

    r = differential_evolution(cost, [(20.0, 110.0), (0.0, 45.0)], seed=0, tol=1e-6, maxiter=200, polish=True)
    zt, ell = r.x
    w = width_for_z(zt, h, er)
    return dict(Zt=zt, Wt=w, Lt=ell, worst_s11_db=r.fun,
                before_db=float(np.max(20 * np.log10(np.abs(gamma[m])))), eeff=microstrip(w, h, er)[1])


def design2(f, gamma, band, h, er, maxlen=22.0, zr=(30.0, 90.0), z0=50.0, seed=1):
    """Two series sections (port side first). Returns widths/lengths and the predicted worst S11 / curve over the band."""
    from scipy.optimize import differential_evolution
    m = (f >= band[0]) & (f <= band[1])

    def chain(g, ff, p):
        for zt, ell in ((p[2], p[3]), (p[0], p[1])):  # load side first
            g = add_line(g, ff, zt, ell, microstrip(width_for_z(zt, h, er), h, er)[1], z0)
        return g

    def cost(p):
        return float(np.max(20 * np.log10(np.abs(chain(gamma[m], f[m], p)) + 1e-9))) + 50 * max(0.0, p[1] + p[3] - maxlen)

    r = differential_evolution(cost, [zr, (0, maxlen), zr, (0, maxlen)], seed=seed, maxiter=300, popsize=25, tol=1e-7)
    p = r.x
    out = dict(Zt1=p[0], Wt1=width_for_z(p[0], h, er), Lt1=p[1], Zt2=p[2], Wt2=width_for_z(p[2], h, er), Lt2=p[3],
               worst_s11_db=float(np.max(20 * np.log10(np.abs(chain(gamma[m], f[m], p))))),
               before_db=float(np.max(20 * np.log10(np.abs(gamma[m])))))
    out["curve_db"] = 20 * np.log10(np.abs(chain(gamma, f, p)))
    return out
