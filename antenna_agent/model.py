"""Simulator-neutral geometry IR. Both backends translate this; geometry is defined once.

Coordinates in mm. z is up. All antennas here are built about the origin.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .design import C0, Design
from .spec import yagi_last_element


@dataclass
class Box:
    name: str
    material: str
    lo: tuple[float, float, float]
    hi: tuple[float, float, float]


@dataclass
class Cyl:  # z-axis cylinder
    name: str
    material: str
    xc: float
    yc: float
    z0: float
    z1: float
    r: float


@dataclass
class Bool:
    op: str  # subtract | unite
    target: str
    tools: list[str]


@dataclass
class Port:
    name: str
    plane: str  # ZX | XY | YZ (sheet orientation)
    origin: tuple[float, float, float]
    sizes: tuple[float, float]  # along the first/second axis of `plane`
    p1: tuple[float, float, float]  # integration line start (reference conductor)
    p2: tuple[float, float, float]  # integration line end
    z0: float = 50.0


@dataclass
class Model:
    name: str
    f0: float
    fmin: float
    fmax: float
    npts: int
    materials: dict[str, tuple[float, float]]  # name -> (er, tan_d)
    solids: list = field(default_factory=list)
    booleans: list[Bool] = field(default_factory=list)
    port: Optional[Port] = None
    air_pad: float = 0.0
    design: Optional[Design] = None  # back-reference (used by the mock backend and de-embedding)
    ref_shift: Optional[tuple[float, float]] = None  # (line length mm, eeff) between port plane and antenna
    fields_ghz: list = field(default_factory=list)  # frequencies where fields/far-field are saved (gain, pattern)

    def bbox(self):
        lo = [1e9] * 3
        hi = [-1e9] * 3
        for s in self.solids:
            if isinstance(s, Box):
                a, b = s.lo, s.hi
            else:
                a, b = (s.xc - s.r, s.yc - s.r, s.z0), (s.xc + s.r, s.yc + s.r, s.z1)
            for i in range(3):
                lo[i] = min(lo[i], a[i])
                hi[i] = max(hi[i], b[i])
        return tuple(lo), tuple(hi)


def ident(s: str) -> str:
    return re.sub(r"\W", "_", s)


def build_model(d: Design, span: float = 0.25, npts: int = 201) -> Model:
    f0 = d.spec.f0_ghz
    fmin, fmax = d.spec.sweep_ghz if d.spec.sweep_ghz else (f0 * (1 - span), f0 * (1 + span))
    pad = C0 / (fmin * 1e9) * 1e3 / 4
    z0 = d.spec.z0_ohm
    fam = d.spec.family
    if fam == "rect_patch":
        m = _patch(d, f0, fmin, fmax, npts, z0)
    elif fam == "printed_yagi":
        m = _yagi(d, f0, fmin, fmax, npts, z0)
    elif fam == "meander":
        m = _meander(d, f0, fmin, fmax, npts, z0)
    elif fam == "dipole":
        m = _dipole(d, f0, fmin, fmax, npts, z0)
    else:
        m = _monopole(d, f0, fmin, fmax, npts, z0)
    m.air_pad = pad
    m.design = d
    return m


def _patch(d, f0, fmin, fmax, npts, z0) -> Model:
    s = d.spec.substrate
    W, L, Wf, Lf, t = d["W"], d["L"], d["Wf"], d["Lf"], d["t"]
    Wg, Lg, y0, gap, h = d["Wg"], d["Lg"], d["y0"], d["inset_gap"], s.h_mm
    sub = "sub_" + ident(s.name)
    y_lo = -L / 2 - Lf
    y_hi = y_lo + Lg
    m = Model("patch", f0, fmin, fmax, npts, {sub: (s.er, s.tan_d)})
    m.solids += [
        Box("gnd", "pec", (-Wg / 2, y_lo, -t), (Wg / 2, y_hi, 0)),
        Box("substrate", sub, (-Wg / 2, y_lo, 0), (Wg / 2, y_hi, h)),
        Box("patch", "pec", (-W / 2, -L / 2, h), (W / 2, L / 2, h + t)),
        # feed overlaps the patch by >= 0.1 mm so the union is a single solid even when y0 == 0
        Box("feed", "pec", (-Wf / 2, y_lo, h), (Wf / 2, -L / 2 + max(y0, 0.1), h + t)),
    ]
    if y0 > 1e-6:
        # notches overshoot the patch edge and span the conductor thickness: robust boolean in both tools
        for nm, (x0, x1) in (("notch_l", (-Wf / 2 - gap, -Wf / 2)), ("notch_r", (Wf / 2, Wf / 2 + gap))):
            m.solids.append(Box(nm, "pec", (x0, -L / 2 - 1.0, h - t), (x1, -L / 2 + y0, h + 2 * t)))
        m.booleans.append(Bool("subtract", "patch", ["notch_l", "notch_r"]))
    m.booleans.append(Bool("unite", "patch", ["feed"]))
    pw = min(max(2 * Wf, 6 * h), Wg)
    m.port = Port("P1", "ZX", (-pw / 2, y_lo, 0.0), (h, pw), (0, y_lo, 0.0), (0, y_lo, h), z0)
    m.ref_shift = (Lf + y0, d.aux["eeff_line"])
    return m


def _dipole(d, f0, fmin, fmax, npts, z0) -> Model:
    L, a, gap = d["L"], d["a"], d["gap"]
    m = Model("dipole", f0, fmin, fmax, npts, {})
    m.solids += [
        Cyl("arm_top", "pec", 0, 0, gap / 2, L / 2, a),
        Cyl("arm_bot", "pec", 0, 0, -L / 2, -gap / 2, a),
    ]
    m.port = Port("P1", "ZX", (-a, 0.0, -gap / 2), (gap, 2 * a), (0, 0, -gap / 2), (0, 0, gap / 2), z0)
    return m


def _monopole(d, f0, fmin, fmax, npts, z0) -> Model:
    L, a, gap, Lg, t = d["L"], d["a"], d["gap"], d["Lg"], d["t"]
    m = Model("monopole", f0, fmin, fmax, npts, {})
    m.solids += [
        Box("gnd", "pec", (-Lg / 2, -Lg / 2, -t), (Lg / 2, Lg / 2, 0)),
        Cyl("wire", "pec", 0, 0, gap, L, a),
    ]
    m.port = Port("P1", "ZX", (-a, 0.0, 0.0), (gap, 2 * a), (0, 0, 0.0), (0, 0, gap), z0)
    return m


def _yagi(d, f0, fmin, fmax, npts, z0) -> Model:
    """4-layer PCB Yagi. x = element axis, y = boresight, z = stack-up (L0 bottom ... L3 top).
    Ground pour on all four layers at y in [-Lp, 0] (reflector), tied by a solid wall standing in for the via fence.
    Driven dipole: top arm (x>0) on L3, bottom arm (x<0) on L2, fed by a two-wire (broadside) strip pair along y.
    Directors on L3. Dielectric is one slab minus the buried copper (no overlapping solids)."""
    s = d.spec.substrate
    t, Bw, Lp = d["tcu"], d["Bw"], d["Lp"]
    Ws, clr, vo = d["Ws"], d["clr"], d["via_off"]
    z0b, z1b = 0.0, t + d["h10"]
    z1t = z1b + t
    z2b = z1t + d["h21"]
    z2t = z2b + t
    z3b = z2t + d["h32"]
    z3t = z3b + t
    y_end = d.aux["y_end"]
    sub = "sub_" + ident(s.name)
    m = Model("printed_yagi", f0, fmin, fmax, npts, {sub: (s.er, s.tan_d)})
    m.fields_ghz = list(d.spec.fields_ghz) if d.spec.fields_ghz else [round(f0, 4)]
    X = Bw / 2
    add, B = m.solids.append, Box

    # --- ground reflector: four pours + via wall (united into one conductor)
    add(B("gnd_L0", "pec", (-X, -Lp, z0b), (X, 0, z0b + t)))
    add(B("gnd_L1", "pec", (-X, -Lp, z1b), (X, 0, z1t)))
    add(B("gnd_L2", "pec", (-X, -Lp, z2b), (X, 0, z2t)))
    add(B("gnd_L3", "pec", (-X, -Lp, z3b), (X, 0, z3t)))
    add(B("via_wall", "pec", (-X, -vo - 0.3, z0b), (X, -vo, z3t)))
    m.booleans.append(Bool("unite", "gnd_L0", ["gnd_L1", "gnd_L2", "gnd_L3", "via_wall"]))

    # --- driven dipole + two-wire feed
    y2 = d["S12"]
    ye = y2 + d["W2"]
    L2h = d["L2"] / 2
    add(B("top_strip", "pec", (-Ws / 2, clr, z3b), (Ws / 2, y2 + 0.5, z3t)))
    add(B("top_arm", "pec", (-Ws / 2, y2, z3b), (L2h, ye, z3t)))
    m.booleans.append(Bool("unite", "top_strip", ["top_arm"]))
    add(B("bot_strip", "pec", (-Ws / 2, clr, z2b), (Ws / 2, y2 + 0.5, z2t)))
    add(B("bot_arm", "pec", (-L2h, y2, z2b), (Ws / 2, ye, z2t)))
    m.booleans.append(Bool("unite", "bot_strip", ["bot_arm"]))

    # --- directors (L3 layer): elements 3..E
    E = yagi_last_element(d.spec.dims_mm)
    y = ye
    for e in range(3, E + 1):
        y += d[f"S{e - 1}{e}"]
        Lk, Wk = d[f"L{e}"], d[f"W{e}"]
        add(B(f"dir{e - 2}", "pec", (-Lk / 2, y, z3b), (Lk / 2, y + Wk, z3t)))
        y += Wk
    y += d[f"S{E}{E + 1}"]
    assert abs(y - y_end) < 1e-6, (y, y_end)

    # --- dielectric: slab up to the bottom of L3, minus the buried copper (duplicates are consumed by the subtract)
    add(B("slab", sub, (-X, -Lp, z0b), (X, y_end, z3b)))
    cuts = []
    for nm, (lo, hi) in {"cut_L0": ((-X, -Lp, z0b), (X, 0, z0b + t)), "cut_L1": ((-X, -Lp, z1b), (X, 0, z1t)),
                         "cut_L2": ((-X, -Lp, z2b), (X, 0, z2t)), "cut_wall": ((-X, -vo - 0.3, z0b), (X, -vo, z3b)),
                         "cut_bot_strip": ((-Ws / 2, clr, z2b), (Ws / 2, y2 + 0.5, z2t)),
                         "cut_bot_arm": ((-L2h, y2, z2b), (Ws / 2, ye, z2t))}.items():
        add(B(nm, "pec", lo, hi))
        cuts.append(nm)
    m.booleans.append(Bool("subtract", "slab", cuts))

    # --- lumped port between the two strips at the start of the two-wire line (integration line: L2 -> L3, +z)
    yp = clr + 0.02  # port plane just inside the strips: sheet/wire ends rest on conductor FACES, not on an end-face edge
    m.port = Port("P1", "ZX", (-Ws / 2, yp, z2t), (d["h32"], Ws), (0, yp, z2t), (0, yp, z3b), z0)
    return m


def _meander(d, f0, fmin, fmax, npts, z0) -> Model:
    """Antipodal meander line. x across the board (centre line x=0), y = end-fire direction, z up.
    Top copper: 50 ohm microstrip + two stubs + meander on x >= 0. Bottom copper: truncated ground (0 <= y <= Gnd),
    strip, and the meander mirrored to x <= 0. Port: lumped, at the board edge y=0, ground -> strip."""
    s = d.spec.substrate
    t, h, Wms = d["t"], s.h_mm, d["Wms"]
    Bw, Bl, Gnd, Lms = d["Bw"], d["Bl"], d["Gnd"], d["Lms"]
    Wrad, Wcon = d["Wrad"], d["Wcon"]
    g = d.aux["geometry"]
    N, ys, dep = g["N"], g["y"], g["depth"]
    sub = "sub_" + ident(s.name)
    m = Model("meander", f0, fmin, fmax, npts, {sub: (s.er, s.tan_d)})
    m.fields_ghz = list(d.spec.fields_ghz) if d.spec.fields_ghz else [round(f0, 4)]
    zt0, zt1, zb0, zb1 = h, h + t, -t, 0.0
    add, B = m.solids.append, Box
    ov = min(0.3, Wrad / 4)  # overlap so unions are volumetric, never face-contact only

    def meander_parts(sign, z0_, z1_, pre):
        """Boxes of one meander on side `sign` (+1 top / -1 bottom); returns names."""
        names = []

        def box(nm, xa, xb, ya, yb):
            lo, hi = sorted((sign * xa, sign * xb))
            add(B(f"{pre}{nm}", "pec", (lo, ya, z0_), (hi, yb, z1_)))
            names.append(f"{pre}{nm}")
        for n in range(N):
            xa = -Wms / 2 if n == 0 else 0.0
            if n == N - 1:  # last bar: free end carries the tail to the board edge
                box(f"bar{n + 1}", xa, dep[n], ys[n] - Wrad / 2, ys[n] + Wrad / 2)
                box("tail", dep[n] - Wrad, dep[n], ys[n] - ov, Bl)
            else:
                box(f"bar{n + 1}", xa, dep[n], ys[n] - Wrad / 2, ys[n] + Wrad / 2)
        for n in range(N - 1):
            ya, yb = ys[n] - Wrad / 2, ys[n + 1] + Wrad / 2
            if n % 2 == 0:  # lower connector joins bars n, n+1 (0-based) at the pair depth
                box(f"con{n + 1}", dep[n] - Wcon, dep[n], ya, yb)
            else:           # upper connector
                box(f"con{n + 1}", 0.0, Wcon, ya, yb)
        return names

    # --- top copper
    y_s = ys[0] + Wrad / 2
    add(B("ms", "pec", (-Wms / 2, 0.0, zt0), (Wms / 2, y_s, zt1)))
    top = meander_parts(+1, zt0, zt1, "t_")
    if "Lstub" in d.p and "Pstub" in d.p:
        ysb = Lms + Wrad - d["Pstub"]
        add(B("stub", "pec", (-Wms / 2 - d["Lstub"], ysb, zt0), (Wms / 2 + d["Lstub"], ysb + Wms, zt1)))
        top.append("stub")
    m.booleans.append(Bool("unite", "ms", top))
    # --- bottom copper
    add(B("gnd", "pec", (-Bw / 2, 0.0, zb0), (Bw / 2, Gnd, zb1)))
    add(B("bstrip", "pec", (-Wms / 2, Gnd - 0.5, zb0), (Wms / 2, y_s, zb1)))
    bot = meander_parts(-1, zb0, zb1, "b_") + ["bstrip"]
    m.booleans.append(Bool("unite", "gnd", bot))
    # --- dielectric
    add(B("substrate", sub, (-Bw / 2, 0.0, 0.0), (Bw / 2, Bl, h)))
    pw = min(max(2 * Wms, 6 * h), Bw)
    m.port = Port("P1", "ZX", (-pw / 2, 0.0, 0.0), (h, pw), (0, 0.0, 0.0), (0, 0.0, h), z0)
    return m
