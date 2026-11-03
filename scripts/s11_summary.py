"""One-line S11 summary of an HFSS s11.csv (numpy only, no other dependency).
Usage: py -3.12 scripts\\s11_summary.py <folder_with_s11.csv> <label> <s> [f_target_GHz=1.795]
Prints resonance, S11 min, Z at the target, -10 dB band and the scale s corrected so the resonance lands on the target
(resonance goes as 1/s: s_new = s * f_res / f_target)."""
import sys
import numpy as np

d, label, s = sys.argv[1], sys.argv[2], float(sys.argv[3])
F_T = float(sys.argv[4]) if len(sys.argv) > 4 else 1.795
a = np.genfromtxt(f"{d}/s11.csv", delimiter=",", names=True)
f, S = a["f_GHz"], a["re"] + 1j * a["im"]
db = 20 * np.log10(np.abs(S) + 1e-12)
k = int(np.argmin(db))
fr = f[k]
if 0 < k < len(f) - 1:  # parabolic refinement of the minimum
    y0, y1, y2 = db[k - 1], db[k], db[k + 1]
    den = y0 - 2 * y1 + y2
    if den:
        fr = f[k] + 0.5 * (y0 - y2) / den * (f[1] - f[0])
z = 50 * (1 + S) / (1 - S)
it = int(np.argmin(abs(f - F_T)))
bw = "no band below -10 dB"
if db[k] < -10:
    lo = hi = k
    while lo > 0 and db[lo - 1] < -10:
        lo -= 1
    while hi < len(f) - 1 and db[hi + 1] < -10:
        hi += 1
    bw = "%.3f-%.3f GHz (%.0f MHz)" % (f[lo], f[hi], 1000 * (f[hi] - f[lo]))
edge = " [WARNING: minimum at the sweep edge, resonance outside the sweep]" if k in (0, len(f) - 1) else ""
print("%s | s=%.4f | f_res=%.3f GHz%s | S11min=%.1f dB | S11(%.3f)=%.1f dB | Z=%.1f%+.1fj | -10 dB band: %s | s for %.3f GHz: %.4f"
      % (label, s, fr, edge, db[k], F_T, db[it], z[it].real, z[it].imag, bw, F_T, s * fr / F_T))
