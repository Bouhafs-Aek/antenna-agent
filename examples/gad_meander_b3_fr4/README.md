# Negative result: retargeting the meander antenna to LTE B3 (1.71-1.88 GHz) on FR4

Scaling rule: s = (f_paper/f_target)·sqrt(eeff_paper/eeff_new), all in-plane lengths x s, N and S unchanged
(nominal s = 1.163; variants below multiply it). Real HFSS Student runs:

| Variant | Board (mm) | S11 min | Worst S11 in B3 | Max VSWR in B3 | Gain at 1.795 GHz |
|---|---|---|---|---|---|
| s104 | 66.5 x 120.9 | -8.2 dB at 1.884 GHz | -4.8 dB | 3.68 | not run |
| s108 | 69.1 x 125.6 | -7.7 dB at 1.839 GHz | -4.6 dB | 3.88 | 8.8 dBi (realised with mismatch 7.7) |
| s112 | 71.6 x 130.2 | -7.4 dB at 1.764 GHz | -4.1 dB | 4.29 | 8.9 dBi (realised 7.9) |

Conclusion: **not matched** (Zin about 20 ohm with capacitive reactance); scaling alone is not enough. Next: stub sweep
(`scripts/make_b3_tune.py`), a matching section, or another stack. FR4 gain looks high for tan d = 0.02 and radiation efficiency
was not checked: do not quote it. Each folder: `spec.yaml`, `hfss_build.py`, `results/` (S11, gain where run, plots).
