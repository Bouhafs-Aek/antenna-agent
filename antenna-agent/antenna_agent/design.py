"""Closed-form antenna design (Balanis, Hammerstad). Fills whatever the paper did not state.

Every parameter carries provenance: "paper" (stated), "derived" (computed here), "tuned" (changed by the solver loop).
Lengths in mm in Design.p; internal maths in SI.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.special import j0

from .spec import AntennaSpec, yagi_last_element

C0 = 299_792_458.0


@dataclass
class P:
    v: float
    src: str  # paper | derived | tuned


@dataclass
class Design:
    spec: AntennaSpec
    p: dict[str, P]
    aux: dict = field(default_factory=dict)

    def __getitem__(self, k: str) -> float:
        return self.p[k].v

    def set(self, k: str, v: float, src: str = "tuned") -> None:
        self.p[k] = P(float(v), src)

    def tunable(self) -> list[str]:
        """Parameters the solver loop may move: only those NOT stated in the paper."""
        keys = {"rect_patch": ["L", "y0"], "dipole": ["L"], "monopole": ["L"], "printed_yagi": [], "meander": []}[self.spec.family]
        return [k for k in keys if self.p[k].src != "paper"]

    def table(self) -> dict:
        return {k: {"mm": round(x.v, 4), "src": x.src} for k, x in self.p.items()}


# ---------------------------------------------------------------- microstrip helpers
def eeff_ms(er: float, u: float) -> float:
    """Hammerstad effective permittivity, u = w/h."""
    e = (er + 1) / 2 + (er - 1) / 2 * (1 + 12 / u) ** -0.5
    if u < 1:
        e += (er - 1) / 2 * 0.04 * (1 - u) ** 2
    return e


def w50_over_h(er: float, z0: float = 50.0) -> float:
    """Hammerstad synthesis: w/h giving characteristic impedance z0."""
    A = z0 / 60 * math.sqrt((er + 1) / 2) + (er - 1) / (er + 1) * (0.23 + 0.11 / er)
    u = 8 * math.exp(A) / (math.exp(2 * A) - 2)
    if u > 2:
        B = 377 * math.pi / (2 * z0 * math.sqrt(er))
        u = 2 / math.pi * (B - 1 - math.log(2 * B - 1)
                           + (er - 1) / (2 * er) * (math.log(B - 1) + 0.39 - 0.61 / er))
    return u


def patch_rin0(W: float, L: float, f0: float, n: int = 20000):
    """Edge input resistance of a rectangular patch, Balanis (14-12)/(14-18). SI units.
    Rin = 1/(2(G1+G12)); full radiation integrals, not the small-W approximation."""
    k0 = 2 * math.pi * f0 / C0
    th = (np.arange(n) + 0.5) * math.pi / n  # midpoint grid, never hits theta=pi/2
    X = k0 * W / 2
    g = (X * np.sinc(X * np.cos(th) / math.pi)) ** 2 * np.sin(th) ** 3
    d = math.pi / n / (120 * math.pi ** 2)
    G1 = float(g.sum() * d)
    G12 = float((g * j0(k0 * L * np.sin(th))).sum() * d)
    return 1 / (2 * (G1 + G12)), G1, G12


def patch_dL(er: float, eeff: float, W: float, h: float) -> float:
    """Hammerstad fringing extension per radiating edge (m)."""
    return 0.412 * h * (eeff + 0.3) * (W / h + 0.264) / ((eeff - 0.258) * (W / h + 0.8))


# ---------------------------------------------------------------- families
def _put(pm: dict, dims: dict, k: str, derived_mm: float) -> None:
    pm[k] = P(float(dims[k]), "paper") if k in dims else P(float(derived_mm), "derived")


def design_patch(spec: AntennaSpec) -> Design:
    s, dims, z0 = spec.substrate, spec.dims_mm, spec.z0_ohm
    er, h, f0 = s.er, s.h_mm * 1e-3, spec.f0_ghz * 1e9
    pm: dict[str, P] = {}
    warn: list[str] = []

    _put(pm, dims, "W", C0 / (2 * f0) * math.sqrt(2 / (er + 1)) * 1e3)
    W = pm["W"].v * 1e-3
    eeff = (er + 1) / 2 + (er - 1) / 2 * (1 + 12 * h / W) ** -0.5
    dL = patch_dL(er, eeff, W, h)
    _put(pm, dims, "L", (C0 / (2 * f0 * math.sqrt(eeff)) - 2 * dL) * 1e3)
    L = pm["L"].v * 1e-3

    _put(pm, dims, "Wf", w50_over_h(er, z0) * h * 1e3)
    Wf = pm["Wf"].v * 1e-3
    eeff_l = eeff_ms(er, Wf / h)
    lamg = C0 / (f0 * math.sqrt(eeff_l))

    _put(pm, dims, "t", 0.035)
    _put(pm, dims, "Wg", (W + 6 * h) * 1e3)
    far_margin = 3 * h
    if "Lg" in dims and "Lf" not in dims:
        lf = dims["Lg"] * 1e-3 - L - far_margin
        if lf < 2 * Wf:
            warn.append("Lg too short to derive Lf; using default feed length")
            lf = max(0.1 * lamg, 4 * Wf)
        _put(pm, dims, "Lf", lf * 1e3)
    else:
        _put(pm, dims, "Lf", max(0.1 * lamg, 4 * Wf) * 1e3)
    Lf = pm["Lf"].v * 1e-3
    _put(pm, dims, "Lg", (L + Lf + far_margin) * 1e3)

    Rin0, G1, G12 = patch_rin0(W, L, f0)
    y0 = L / math.pi * math.acos(math.sqrt(min(1.0, z0 / Rin0)))
    _put(pm, dims, "y0", y0 * 1e3)
    _put(pm, dims, "inset_gap", max(0.2, lamg * 1e3 / 60))

    if pm["Lg"].v < pm["L"].v + pm["Lf"].v:
        warn.append("Lg < L + Lf: substrate shorter than patch + feed; check paper dims")
    if pm["y0"].v >= pm["L"].v / 2:
        warn.append("inset depth >= L/2")
    aux = dict(eeff=eeff, dL_mm=dL * 1e3, eeff_line=eeff_l, lamg_mm=lamg * 1e3,
               Rin0=Rin0, G1=G1, G12=G12, warnings=warn)
    return Design(spec, pm, aux)


def design_dipole(spec: AntennaSpec) -> Design:
    lam = C0 / (spec.f0_ghz * 1e9) * 1e3
    pm: dict[str, P] = {}
    _put(pm, spec.dims_mm, "L", 0.48 * lam)  # thin-wire start point; solver loop trims end effects
    _put(pm, spec.dims_mm, "a", lam / 400)
    _put(pm, spec.dims_mm, "gap", lam / 150)
    return Design(spec, pm, dict(lam_mm=lam, warnings=[]))


def design_monopole(spec: AntennaSpec) -> Design:
    lam = C0 / (spec.f0_ghz * 1e9) * 1e3
    pm: dict[str, P] = {}
    _put(pm, spec.dims_mm, "L", 0.24 * lam)
    _put(pm, spec.dims_mm, "a", lam / 400)
    _put(pm, spec.dims_mm, "gap", lam / 150)
    _put(pm, spec.dims_mm, "Lg", 1.0 * lam)
    _put(pm, spec.dims_mm, "t", 0.035)
    return Design(spec, pm, dict(lam_mm=lam, warnings=[]))


def design_printed_yagi(spec: AntennaSpec) -> Design:
    """No closed form: every dimension must come from the paper. Only the pour length, port clearance and via-fence
    offset may be derived/assumed."""
    d, pm = spec.dims_mm, {}
    for k, v in d.items():
        pm[k] = P(float(v), "paper")
    warn = []
    # board front edge measured along boresight, assuming the S gaps are edge-to-edge (as drawn in the paper's Fig. 2)
    E = yagi_last_element(d)
    y_end = sum(d[f"S{e - 1}{e}"] + d[f"W{e}"] for e in range(2, E + 1)) + d[f"S{E}{E + 1}"]
    if "Lp" not in d:
        pm["Lp"] = P(d["Bl"] - y_end, "derived")
        warn.append(f"pour length not stated: Lp = Bl - sum(S, W) = {d['Bl'] - y_end:.2f} mm (assumes S gaps are edge-to-edge)")
    if pm["Lp"].v <= 5:
        warn.append("pour length <= 5 mm: check dims")
    if "clr" not in d:
        pm["clr"] = P(0.5, "derived")
        warn.append("port clearance 0.5 mm between pour edge and port plane is a modelling choice")
    if "via_off" not in d:
        pm["via_off"] = P(1.0, "derived")
        warn.append("via fence modelled as a solid PEC wall 1.0 mm behind the pour edge (via positions not in the paper)")
    warn.append("printed balun NOT modelled: replaced by an ideal lumped port on the two-wire line "
                "(50 ohm per the paper's text). S11 is not comparable to the published S11.")
    if not spec.substrate.tan_d:
        warn.append("tan_d not given: 0 assumed")
    return Design(spec, pm, dict(y_end=y_end, n_directors=E - 2, warnings=warn))


def meander_geometry(d) -> dict:
    """Description of the meander (mm), shared by model.py. Radiator n (1..N) is a bar of width Wrad at y_n; bars are
    joined alternately by lower connectors (outer rail at x = depth) and upper connectors (x = 0..Wcon). A lower
    connector serves the pair (2k-1, 2k); its outer rail sits at e_k = S^(k-1) (Lr1 + Wcon), k = 1, 2, ...
    Read from Fig. 11 of the paper (rails measured 24.7/22.2/20.8/19.1 mm; this rule gives 24.5/22.5/20.7/19.1)."""
    N, S = int(round(d["N"])), d["S"]
    Wrad, Wcon, Lcon = d["Wrad"], d["Wcon"], d["Lcon"]
    e = [S ** k * (d["Lr1"] + Wcon) for k in range((N + 1) // 2)]
    y = [d["Lms"] + Wrad / 2 + n * Lcon for n in range(N)]
    depth = [e[n // 2] for n in range(N)]
    return dict(N=N, e=e, y=y, depth=depth)


def design_meander(spec: AntennaSpec) -> Design:
    """Antipodal meander line (Gad & Sallam, Sci. Rep. 14:5769). Everything is paper-stated; only the 50 ohm
    microstrip width and copper thickness are derived (Hammerstad)."""
    d, s, pm, warn = spec.dims_mm, spec.substrate, {}, []
    for k, v in d.items():
        pm[k] = P(float(v), "paper")
    if "Wms" not in d:
        pm["Wms"] = P(w50_over_h(s.er, spec.z0_ohm) * s.h_mm, "derived")
        warn.append(f"50 ohm microstrip width not stated: Hammerstad gives {pm['Wms'].v:.3f} mm for er={s.er}, h={s.h_mm}")
    if "t" not in d:
        pm["t"] = P(0.035, "derived")
        warn.append("copper thickness 35 um assumed")
    g = meander_geometry({k: v.v for k, v in pm.items()})
    y_right = g["y"][-1] + d["Wrad"] / 2
    if y_right > d["Bl"] + 1e-9:
        warn.append(f"last radiator ends at y={y_right:.2f} mm beyond the board length {d['Bl']} mm")
    if g["e"][0] > d["Bw"] / 2:
        warn.append(f"radiator 1 half-length {g['e'][0]:.2f} mm exceeds half the board width")
    warn.append("meander rail depths (one lower rail per pair of radiators, scaled by S per pair) are read from the paper's "
                "Fig. 11, not stated numerically; the text states only Lr_n = S*Lr_(n-1)")
    warn.append("stub position convention (left edge, measured from the right edge of radiator 1) is read from Fig. 6b")
    warn.append("SMA connector not modelled: ideal 50 ohm lumped port at the board edge between strip and ground")
    if not s.tan_d:
        warn.append("tan_d not given: 0 assumed")
    return Design(spec, pm, dict(geometry=g, L_eq=2 * g["e"][0], warnings=warn))


def make_design(spec: AntennaSpec) -> Design:
    return {"rect_patch": design_patch, "dipole": design_dipole, "monopole": design_monopole,
            "printed_yagi": design_printed_yagi, "meander": design_meander}[spec.family](spec)
