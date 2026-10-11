"""LTE B3 (1710-1880 MHz) printed Yagi on 1.6 mm FR4: optimise in the calibrated effective-medium MoM model.
Parameters (PCB mm): driven length Ld, pour->driven gap g0, director length L1 + linear taper t, gap s1 + growth u."""
import json
import sys
from dataclasses import asdict

import numpy as np
from scipy.optimize import minimize

from antenna_agent import yagi_mom as Y

K = 0.80                       # calibrated on DN034 (directivity + S11 band centre)
BAND = (1.71, 1.795, 1.88)     # optimisation points, GHz
CHECK = np.round(np.linspace(1.65, 1.94, 7), 3)
WD, WDIR = 4.15, 5.18          # strip widths: DN034 widths x (2.44/1.795)
BW, LP, END = 136.0, 50.0, 25.0  # pour width/length (DN034 x 1.36), end margin past last director


def make(x, n):
    Ld, g0, L1, t, s1, u = x
    L = [Ld] + [L1 - t * i for i in range(n)]
    W = [WD] + [WDIR] * n
    gap = [g0] + [s1 + u * i for i in range(n)]
    return Y.Yagi(L=L, W=W, gap=gap, Bw=BW, Lp=LP)


def evaluate(yg, freqs=BAND, k=K):
    return [Y.analyze(yg, k, f) for f in freqs]


def cost(x, n):
    Ld, g0, L1, t, s1, u = x
    if min(Ld, g0, L1, s1) < 8 or t < 0 or s1 + u * (n - 1) < 8 or L1 - t * (n - 1) < 25:
        return 1e3
    r = evaluate(make(x, n))
    d = np.array([q["gain_dbi"] for q in r]); fb = np.array([q["fb_db"] for q in r])
    s = np.array([q["s11_db"] for q in r]); fwd = np.array([q["theta"] == 90 and q["phi"] == 90 for q in r])
    pen = 20.0 * (~fwd).sum()                                   # beam must point down the boom
    pen += 0.3 * np.sum(np.maximum(0, 16 - fb) ** 2)            # F/B >= 16 dB
    pen += 0.15 * np.sum(np.maximum(0, s + 10) ** 2)            # |S11| <= -10 dB vs 50 ohm at the dipole terminals
    return -d.mean() + pen


def start(n):
    f = 2.44 / 1.795  # DN034 scaled to B3
    return [44.96 * f, 16.0 * f, 34.29 * f, 0.8, 15.49 * f, 0.6]


if __name__ == "__main__":
    ns = [int(a) for a in sys.argv[1:]] or [3, 5, 6, 7, 8, 9]
    out = {}
    for n in ns:
        x0 = start(n)
        best = minimize(cost, x0, args=(n,), method="Nelder-Mead",
                        options=dict(xatol=0.05, fatol=0.01, maxiter=400, initial_simplex=None))
        best = minimize(cost, best.x, args=(n,), method="Powell", options=dict(xtol=0.05, ftol=1e-3, maxiter=6))
        yg = make(best.x, n)
        r = evaluate(yg, CHECK)
        board_len = LP + sum(yg.gap) + sum(yg.W) + END
        out[n] = dict(x=list(map(float, best.x)), cost=float(best.fun), board_mm=[BW + 10, round(board_len, 1)],
                      f=CHECK.tolist(), dir=[round(q["gain_dbi"], 2) for q in r], fb=[round(q["fb_db"], 1) for q in r],
                      s11=[round(q["s11_db"], 1) for q in r], z=[f"{q['z']:.0f}" for q in r], yagi=asdict(yg))
        print(f"n={n}: board {BW + 10:.0f} x {board_len:.0f} mm  cost={best.fun:.2f}")
        print("   f   ", CHECK.tolist()); print("   Dir ", out[n]["dir"]); print("   F/B ", out[n]["fb"]); print("   S11 ", out[n]["s11"])
        sys.stdout.flush()
    json.dump(out, open(f"/tmp/b3_opt_{'_'.join(map(str, ns))}.json", "w"), indent=1, default=str)
