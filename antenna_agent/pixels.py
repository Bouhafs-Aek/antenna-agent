"""Pixelated cut-outs ("decoupes") in the copper of the meander, optimised with HFSS in the loop.

The top meander (x >= 0) is tiled into removable cells of ~`cell` mm. A candidate = set of removed cells, stored in
the spec as `cut_<k>: 1` keys of dims_mm (so a candidate is just a spec). Cuts are mirrored on the bottom meander
(antipodal, same x -> -x). Candidates that disconnect the feed from the tail are rejected (raster flood fill).
The search is a surrogate-guided local search (GP on the binary mask + Expected Improvement over blob/flip moves
around the best mask), because 100+ binary variables cannot be searched exhaustively at 5-10 min per HFSS run.
"""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import numpy as np
import yaml

R = 0.25  # raster pitch (mm) for connectivity


def meander_boxes(spec) -> tuple[list, tuple]:
    """Top-copper rectangles (x0,x1,y0,y1) of the base design, feed point and tail point."""
    from .design import make_design
    from .model import Box, build_model
    sp = spec.model_copy(deep=True)
    sp.dims_mm = {k: v for k, v in sp.dims_mm.items() if not k.startswith("cut_")}
    m = build_model(make_design(sp))
    bx = [s for s in m.solids if isinstance(s, Box) and (s.name.startswith("t_") or s.name == "ms")]
    rects = [(s.lo[0], s.hi[0], s.lo[1], s.hi[1]) for s in bx]
    ms = next(s for s in bx if s.name == "ms")
    tail = next(s for s in bx if s.name == "t_tail")
    return rects, ((0.0, 0.5 * ms.hi[1]), (0.5 * (tail.lo[0] + tail.hi[0]), tail.hi[1] - 0.3)), \
        [(s.lo[0], s.hi[0], s.lo[1], s.hi[1]) for s in bx if s.name == "ms"][0]


def cells(spec, cell: float = 2.0) -> list[tuple[float, float, float, float]]:
    """Removable cells: each meander bar/connector is divided into ~cell-sized tiles; overlaps with earlier tiles are
    dropped; the feed microstrip, the tail and the end of the first bar are never removable."""
    rects, (_, tailpt), ms = meander_boxes(spec)
    out, taken = [], []
    for (x0, x1, y0, y1) in rects:
        if (x0, x1, y0, y1) == ms or x0 >= x1 or y0 >= y1:
            continue
        nx, ny = max(1, round((x1 - x0) / cell)), max(1, round((y1 - y0) / cell))
        for i in range(nx):
            for j in range(ny):
                c = (x0 + (x1 - x0) * i / nx, x0 + (x1 - x0) * (i + 1) / nx,
                     y0 + (y1 - y0) * j / ny, y0 + (y1 - y0) * (j + 1) / ny)
                a = (c[1] - c[0]) * (c[3] - c[2])
                ov = sum(max(0, min(c[1], t[1]) - max(c[0], t[0])) * max(0, min(c[3], t[3]) - max(c[2], t[2])) for t in taken)
                if ov > 0.5 * a:
                    continue
                taken.append(c)
                if c[1] > tailpt[0] - 3 and c[3] > tailpt[1] - 8 and c[2] > rects[-1][2] - 0:  # keep the tail strip
                    continue
                out.append(tuple(round(v, 4) for v in c))
    return out


def _raster(spec):
    rects, (feed, tail), _ = meander_boxes(spec)
    xs = [r[0] for r in rects] + [r[1] for r in rects]; ys = [r[2] for r in rects] + [r[3] for r in rects]
    x0, y0 = min(xs), min(ys)
    ix = lambda v: int(round((v - x0) / R)); iy = lambda v: int(round((v - y0) / R))
    g = np.zeros((ix(max(xs)) + 2, iy(max(ys)) + 2), bool)
    for (a, b, c, d) in rects:
        g[ix(a):ix(b), iy(c):iy(d)] = True
    return g, ix, iy, (ix(feed[0]), iy(feed[1])), (ix(tail[0]), iy(tail[1]))


_RC: dict = {}


def connected(spec, cl, removed: set[int]) -> bool:
    from scipy import ndimage
    key = id(spec)
    if key not in _RC:
        _RC.clear(); _RC[key] = _raster(spec)
    g0, ix, iy, s, t = _RC[key]
    g = g0.copy()
    for k in removed:
        a, b, c, d = cl[k]
        g[ix(a):ix(b), iy(c):iy(d)] = False
    if not (g[s] and g[t]):
        return False
    lab, _ = ndimage.label(g)
    return bool(lab[s] == lab[t])


def _cuts_in(spec_dims: dict) -> set[int]:
    return {int(k[4:]) for k, v in spec_dims.items() if k.startswith("cut_") and v}


def _moves(rng, cl, base: set[int], n: int) -> list[set[int]]:
    """Blob and flip moves around `base`: pick a random cell and toggle it plus its spatial neighbours."""
    cen = np.array([[(c[0] + c[1]) / 2, (c[2] + c[3]) / 2] for c in cl])
    out = []
    for _ in range(n):
        s = set(base)
        for _ in range(rng.integers(1, 3)):
            i = int(rng.integers(len(cl)))
            r = rng.choice([0.1, 2.5, 4.5])
            for j in np.where(np.linalg.norm(cen - cen[i], axis=1) <= r)[0]:
                s ^= {int(j)}
        out.append(s)
    return out


def optimise_pixels(spec_path: str, out: str, budget: int = 40, n_init: int = 6, cell: float = 2.0, mock: bool = False,
                    student: bool = True, seed: int = 0, margin: float = 0.1) -> dict:
    from .agent import run
    from .optimize import _gp_ei, _mock, score_run
    from .simulate import simulate
    from .spec import load_spec
    spec = load_spec(spec_path)
    cl = cells(spec, cell)
    out_p = Path(out); out_p.mkdir(parents=True, exist_ok=True)
    (out_p / "cells.json").write_text(json.dumps(cl))
    f0, M = spec.f0_ghz, len(cl)
    hp = out_p / "history.csv"
    hist = list(csv.DictReader(open(hp))) if hp.exists() else []
    rng = np.random.default_rng(seed + len(hist))
    print(f"{M} removable cells of ~{cell} mm")
    vec = lambda s: np.array([1.0 if i in s else 0.0 for i in range(M)])
    while len(hist) < budget:
        i = len(hist) + 1
        ok = [h for h in hist if str(h["ok"]) == "1"]
        best = max(ok, key=lambda h: float(h["score"])) if ok else None
        base = {int(x) for x in best["cuts"].split()} if best and best["cuts"] else set()
        if i == 1:
            cur = set()
        else:
            pool = [c for c in _moves(rng, cl, set() if i <= n_init else base, 1200)
                    if c and connected(spec, cl, c)][:400]
            if i <= n_init or len(ok) < 3:
                cur = pool[0]
            else:
                X = np.array([vec({int(x) for x in h["cuts"].split()}) for h in ok]); y = np.array([float(h["score"]) for h in ok])
                seen = {h["cuts"] for h in hist}
                pool = [c for c in pool if " ".join(map(str, sorted(c))) not in seen] or pool
                cur = pool[int(np.argmax(_gp_ei(X, y, np.array([vec(c) for c in pool]))))]
        cstr = " ".join(map(str, sorted(cur)))
        rd = out_p / f"run_{i:03d}"
        if mock:
            w = np.random.default_rng(1).normal(0, 0.12, M); w[:M // 3] *= -1
            res = _mock(dict(N=7, S=.92, Lr1=18.5, Wrad=4, Lms=26.5, Lcon=10.5, Wcon=6)); res["score"] = res["real_gain_f0"] = res["gain_f0"] = 9.6 + float(sum(w[k] for k in cur))
        else:
            rd.mkdir(parents=True, exist_ok=True)
            si = yaml.safe_load(Path(spec_path).read_text()); si["name"] = f"{spec.name}_px{i:03d}"
            si["dims_mm"].update({f"cut_{k}": 1 for k in cur}); si["cell_mm"] = cell
            (rd / "spec_in.yaml").write_text(yaml.safe_dump(si, sort_keys=False))
            try:
                run(None, str(rd), "hfss", str(rd / "spec_in.yaml"), False, True, 0, False, 0.25)
                simulate(rd, None, student, False)
                res = score_run(rd / "out_hfss", f0, margin)
            except Exception as ex:
                (rd / "error.txt").write_text(str(ex)); res = None
        row = dict(run=i, ok=int(res is not None), score=(res or {}).get("score", -5.0), ncut=len(cur), cuts=cstr,
                   gain_f0=(res or {}).get("gain_f0", ""), real_gain_f0=(res or {}).get("real_gain_f0", ""),
                   s11_f0=(res or {}).get("s11_f0", ""), s11_worst=(res or {}).get("s11_worst", ""))
        hist.append(row)
        new = not hp.exists()
        with open(hp, "a", newline="") as fh:
            w_ = csv.DictWriter(fh, list(row)); new and w_.writeheader(); w_.writerow(row)
        print(f"[{i}/{budget}] score={row['score']} gain={row['real_gain_f0']} s11={row['s11_f0']} cuts={len(cur)}")
    ok = [h for h in hist if str(h["ok"]) == "1"]
    b = max(ok, key=lambda h: float(h["score"])) if ok else {}
    (out_p / "best.json").write_text(json.dumps(b, indent=2))
    if b:
        _plot(cl, {int(x) for x in b["cuts"].split()}, out_p / "best_pixels.png")
    return b


def _plot(cl, removed, path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4, 8))
    for k, (a, b, c, d) in enumerate(cl):
        ax.add_patch(plt.Rectangle((a, c), b - a, d - c, fc="white" if k in removed else "#b87333", ec="k", lw=.3))
    ax.autoscale(); ax.set_aspect("equal"); ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
    fig.savefig(path, dpi=130, bbox_inches="tight"); plt.close(fig)
