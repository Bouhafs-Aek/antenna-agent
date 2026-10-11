# Results

## 1. Paper replica (validation) - Gad & Sallam, Sci. Rep. 14:5769
Dimensions exactly as in the paper (RO3003, 2.45 GHz).
| Quantity | Paper | This repo (HFSS Student) |
|---|---|---|
| -10 dB band | 2.2-2.7 GHz | 2.155-2.695 GHz |
| S11 min | - | -27.4 dB at 2.455 GHz |
| Peak gain | see paper | 9.6 dBi at 2.45 GHz, Theta 90, Phi 90 (+y) |
Worst S11 inside 2.2-2.7 GHz: -9.1 dB at 2.70 GHz (VSWR 2.08).

## 2. LTE B3 (1.71-1.88 GHz) on FR4 - negative result
Scaling rule: s = (f_paper/f_target) * sqrt(eeff_paper/eeff_new), eeff from Hammerstad for a 50 ohm line; all in-plane
lengths x s; N and S unchanged. Nominal s = 1.163, variants s = 1.00-1.12.
Outcome: Zin about 20 ohm with -20..-25 ohm reactance, S11 min only -7.4..-8.2 dB. Scaling alone does not match;
the minimum would centre on 1.795 GHz around s = 1.10 but stays unmatched. Next: stub sweep (`scripts/make_b3_tune.py`),
a matching section on the feed, or a different stack. Gain on FR4 (about 8.4-8.9 dBi excl. about 1 dB mismatch) looks high
for tan d = 0.02 and is unconfirmed: check radiation efficiency before quoting it.
