"""Solver-in-the-loop correction of parameters the paper did NOT state. Paper-stated dimensions are never moved."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from .backends import Backend
from .design import Design
from .metrics import Metrics, SResult, compute
from .model import build_model

F_TOL = 0.01  # |f_res/f0 - 1|
MATCH_DB = -10.0


@dataclass
class Iter:
    k: int
    params: dict
    metrics: Metrics
    result: SResult


@dataclass
class TuneOutcome:
    history: list[Iter] = field(default_factory=list)
    converged: bool = False
    note: str = ""


def _step(d: Design, m: Metrics) -> list[str]:
    """Apply one physics-based correction. Returns the list of parameters changed."""
    f0, z0, fam = d.spec.f0_ghz, d.spec.z0_ohm, d.spec.family
    tun, changed = d.tunable(), []
    ratio = m.f_res_ghz / f0
    if "L" in tun and abs(ratio - 1) > F_TOL / 4:
        if fam == "rect_patch":  # f ~ 1/(L + 2 dL): rescale the effective length
            dl2 = 2 * d.aux["dL_mm"]
            new = (d["L"] + dl2) * ratio - dl2
        else:
            new = d["L"] * ratio
        d.set("L", min(max(new, 0.7 * d["L"]), 1.3 * d["L"]))
        changed.append("L")
    if fam == "rect_patch" and "y0" in tun and m.z_res is not None and m.s11_min_db > MATCH_DB:
        # Rin(y0) = Rin(0) cos^2(pi y0 / L): back out Rin(0) from the measured resistance, then re-solve for Z0.
        r, L, y0 = m.z_res.real, d["L"], d["y0"]
        c2 = math.cos(math.pi * y0 / L) ** 2
        if r > 0 and c2 > 1e-6:
            rin0 = r / c2
            new = L / math.pi * math.acos(math.sqrt(min(1.0, z0 / rin0)))
            d.set("y0", min(max(new, 0.0), 0.45 * L))
            changed.append("y0")
    return changed


def tune(d: Design, backend: Backend, workdir: Path, max_iter: int = 6, span: float = 0.25, npts: int = 201,
         allow_moves: bool = True) -> TuneOutcome:
    out = TuneOutcome()
    for k in range(max_iter):
        it_dir = workdir / f"iter{k:02d}"
        model = build_model(d, span=span, npts=npts)
        res = backend.run(model, it_dir)
        m = compute(res, d.spec.z0_ohm, model.ref_shift)
        out.history.append(Iter(k, d.table(), m, res))
        f_ok = abs(m.f_res_ghz / d.spec.f0_ghz - 1) <= F_TOL
        match_ok = m.s11_min_db <= MATCH_DB
        if f_ok and match_ok:
            out.converged, out.note = True, "frequency and match within tolerance"
            return out
        if not allow_moves or not d.tunable():
            out.note = ("all adjustable parameters were stated in the paper; reporting the as-published result"
                        if not d.tunable() else "tuning disabled")
            return out
        if k == max_iter - 1:  # do not move parameters after the last solve: reported design == simulated design
            break
        before = {p: d[p] for p in d.tunable()}
        changed = _step(d, m)
        if not changed:
            out.note = "no admissible correction left (f ok, match not improvable by remaining parameters)"
            return out
        if all(abs(d[p] - before[p]) < 1e-4 for p in changed):
            out.note = "parameters stopped moving"
            return out
    out.note = f"not converged after {max_iter} iterations"
    return out
