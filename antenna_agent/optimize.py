"""Bayesian optimisation of a meander antenna around HFSS (ask/tell, resumable, no API key).

HFSS is a slow oracle (5-10 min per run on Student), so we fit a Gaussian-process surrogate on the runs done so far and
pick the next geometry by Expected Improvement. Every run is appended to <out>/history.csv; re-running the same command
resumes. Objective = realised gain at f0 (dBi) minus a penalty when S11 > -10 dB inside [f0-margin, f0+margin].
Nothing here invents a gain value: every number comes from your own HFSS run (or --mock for a dry run of the loop).
"""
from __future__ import annotations

import csv
import json
import math
import shutil
from pathlib import Path

import numpy as np
import yaml

# name: (low, high, is_int)  -- defaults bracket the paper's Table 1 design (N=7, S=0.92, Lcon=10.5, ...)
SPACE = {
    "N": (5, 12, True),
    "S": (0.88, 1.00, False),
    "Lcon": (8.5, 14.0, False),
    "Lr1": (15.0, 22.0, False),
    "Wrad": (2.5, 6.0, False),
    "Wcon": (4.0, 8.0, False),
    "Lms": (20.0, 32.0, False),
    "Bw": (50.0, 70.0, False),
    # parametric slots (0 = no slot); not in the default search, enable with --params scw scl srw srl
    "scw": (0.0, 2.5, False),
    "scl": (0.0, 0.9, False),
    "srw": (0.0, 2.0, False),
    "srl": (0.0, 0.9, False),
    # feed matching (series sections, see match.py) and stub; for --objective match
    "Wt1": (3.0, 9.0, False),
    "Lt1": (2.0, 24.0, False),
    "Wt2": (0.6, 3.5, False),
    "Lt2": (1.0, 10.0, False),
    "Lstub": (3.0, 14.0, False),
    "Pstub": (10.0, 45.0, False),
}
DEFAULT_KEYS = ["N", "S", "Lcon", "Lr1", "Wrad", "Wcon", "Lms", "Bw"]
MAX_BOARD_LEN = 220.0  # mm, practical cap on Bl (Bl is derived from the array length)
FIELDS = ["run", "ok", "score", "gain_f0", "real_gain_f0", "s11_f0", "s11_worst", "Bl"] + list(SPACE)


def _decode(u: np.ndarray, keys) -> dict:
    out = {}
    for x, k in zip(u, keys):
        lo, hi, isint = SPACE[k]
        v = lo + float(np.clip(x, 0, 1)) * (hi - lo)
        out[k] = int(round(v)) if isint else round(v, 3)
    return out


def _encode(p: dict, keys) -> np.ndarray:
    return np.array([(p[k] - SPACE[k][0]) / (SPACE[k][1] - SPACE[k][0]) for k in keys])


def board_length(p: dict, base: dict) -> float:
    """Bl follows the array: feed line Lms + N*Lcon + end margin (same rule as the paper's 100 mm / N=7 / Lms 26.5)."""
    margin = base["Bl"] - base["Lms"] - base["N"] * base["Lcon"]
    q = {**base, **p}
    return round(q["Lms"] + q["N"] * q["Lcon"] + margin, 2)


def score_run(out_hfss: Path, f0: float, margin: float = 0.1, band=None, objective: str = "gain") -> dict | None:
    s, g = out_hfss / "s11.csv", out_hfss / "gain.csv"
    if not (s.exists() and g.exists()):
        return None
    a = np.genfromtxt(s, delimiter=",", names=True)
    f, gam = a[a.dtype.names[0]], a[a.dtype.names[1]] + 1j * a[a.dtype.names[2]]
    s11 = 20 * np.log10(np.maximum(np.abs(gam), 1e-9))
    lo, hi = band if band else (f0 - margin, f0 + margin)
    inb = (f >= lo) & (f <= hi)
    s11_f0 = float(np.interp(f0, f, s11))
    worst = float(s11[inb].max()) if inb.any() else s11_f0
    b = np.genfromtxt(g, delimiter=",", names=True)
    gn = float(np.interp(f0, b[b.dtype.names[0]], b[b.dtype.names[1]]))
    mism = 10 * math.log10(max(1 - 10 ** (s11_f0 / 10), 1e-6))
    real = gn + mism
    score = -worst if objective == "match" else real - max(0.0, worst + 10.0)
    return dict(gain_f0=gn, real_gain_f0=real, s11_f0=s11_f0, s11_worst=worst, score=score)


def _mock(p: dict) -> dict:
    """Synthetic response for testing the loop only (NOT physics)."""
    g = 9.6 + 0.35 * (p["N"] - 7) - 25 * (p["S"] - 0.95) ** 2 - 0.02 * (p["Lr1"] - 18.5) ** 2 - 0.5 * (p["Wrad"] - 4) ** 2
    g -= 0.02 * (p["Lms"] - 26.5) ** 2 + 0.01 * (p["Lcon"] - 10.5) ** 2
    s = -12 - 0.4 * abs(p["Wcon"] - 6)
    return dict(gain_f0=g, real_gain_f0=g, s11_f0=s, s11_worst=s + 1, score=g)


def _read_hist(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def _gp_ei(X: np.ndarray, y: np.ndarray, cand: np.ndarray) -> np.ndarray:
    from scipy.stats import norm
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
    k = ConstantKernel(1.0) * Matern(length_scale=np.ones(X.shape[1]) * 0.5, nu=2.5) + WhiteKernel(1e-3)
    gp = GaussianProcessRegressor(k, normalize_y=True, n_restarts_optimizer=3, random_state=0).fit(X, y)
    mu, sd = gp.predict(cand, return_std=True)
    z = (mu - y.max() - 0.01) / np.maximum(sd, 1e-9)
    return (mu - y.max() - 0.01) * norm.cdf(z) + sd * norm.pdf(z)


def propose(hist: list[dict], keys, n_init: int, rng: np.random.Generator, base: dict) -> dict:
    d = len(keys)
    done = [h for h in hist if str(h["ok"]) == "1"]
    if len(hist) < n_init or len(done) < 3:
        if not hist:  # first run = the paper's design: gives a baseline and anchors the GP
            return {k: base[k] for k in keys}
        return _decode(rng.random(d), keys)
    X = np.array([_encode({k: float(h[k]) for k in keys}, keys) for h in done])
    y = np.array([float(h["score"]) for h in done])
    cand = rng.random((4000, d))
    cand = np.vstack([cand, np.clip(X[y.argmax()] + 0.08 * rng.standard_normal((1000, d)), 0, 1)])
    ei = _gp_ei(X, y, cand)
    for i in np.argsort(-ei):
        p = _decode(cand[i], keys)
        if board_length(p, base) <= MAX_BOARD_LEN:
            return p
    return _decode(cand[int(np.argmax(ei))], keys)


def optimise(spec_path: str, out: str, budget: int = 40, n_init: int = 8, keys=None, mock: bool = False,
             student: bool = True, seed: int = 0, margin: float = 0.1, objective: str = "gain", band=None) -> dict:
    from .agent import run
    from .simulate import simulate
    keys = list(keys or DEFAULT_KEYS)
    out_p = Path(out)
    out_p.mkdir(parents=True, exist_ok=True)
    spec = yaml.safe_load(Path(spec_path).read_text())
    base, f0 = dict(spec["dims_mm"]), float(spec["f0_ghz"])
    for k in ("scw", "scl", "srw", "srl"):
        base.setdefault(k, 0.0)
    for k in ("Wt1", "Lt1", "Wt2", "Lt2"):
        base.setdefault(k, 0.0)
    if objective == "match" and band is None and spec.get("fields_ghz"):
        band = (min(spec["fields_ghz"]), max(spec["fields_ghz"]))
    hist_p = out_p / "history.csv"
    hist = _read_hist(hist_p)
    rng = np.random.default_rng(seed + len(hist))
    while len(hist) < budget:
        i = len(hist) + 1
        p = propose(hist, keys, n_init, rng, base)
        dims = dict(base); dims.update(p); dims["Bl"] = board_length(p, base)
        if "Bw" not in keys:
            dims["Bw"] = base["Bw"]
        if dims.get("Lt1", 0) > 0:  # matching sections live over the truncated ground
            dims["Gnd"] = round(max(base["Gnd"], dims["Lt1"] + dims.get("Lt2", 0) + 2.0), 2)
        rd = out_p / f"run_{i:03d}"
        if mock:
            res = _mock(dims)
        else:
            spec_i = dict(spec); spec_i["dims_mm"] = dims; spec_i["name"] = f"{spec['name']}_opt{i:03d}"
            rd.mkdir(parents=True, exist_ok=True)
            sp = rd / "spec_in.yaml"
            sp.write_text(yaml.safe_dump(spec_i, sort_keys=False))
            try:
                run(None, str(rd), "hfss", str(sp), False, True, 0, False, 0.25)
                simulate(rd, None, student, False)
                res = score_run(rd / "out_hfss", f0, margin, band, objective)
            except Exception as ex:  # a failed/over-mesh run is data too: it teaches the GP where not to go
                (rd / "error.txt").write_text(str(ex))
                res = None
        row = {k: "" for k in FIELDS}
        row.update(run=i, Bl=dims["Bl"], **{k: dims[k] for k in keys})
        if res is None:
            row.update(ok=0, score=-5.0)  # pessimistic placeholder; excluded from the GP fit
        else:
            row.update(ok=1, **{k: f"{v:.4f}" for k, v in res.items()})
        hist.append(row)
        new = not hist_p.exists()
        with open(hist_p, "a", newline="") as fh:
            w = csv.DictWriter(fh, FIELDS); new and w.writeheader(); w.writerow(row)
        shutil.rmtree(rd / "out_hfss" / "antenna.aedt.auto", ignore_errors=True)
        print(f"[{i}/{budget}] score={row['score']} gain={row['real_gain_f0']} s11={row['s11_f0']} {p}")
    ok = [h for h in hist if str(h["ok"]) == "1"]
    best = max(ok, key=lambda h: float(h["score"])) if ok else None
    (out_p / "best.json").write_text(json.dumps(best, indent=2))
    return best or {}
