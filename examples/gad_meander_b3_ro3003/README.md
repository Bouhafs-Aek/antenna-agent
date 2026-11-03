# Gad & Sallam meander shifted to LTE B3 (1.71-1.88 GHz): pure scaling, same RO3003, no matching network

**Real HFSS Student 2025 R2 results.** Rule: every in-plane length x s, s = 2.455 / 1.795 = 1.368 (2.455 GHz = S11 minimum
of our replica, `../gad_meander_replica`). Same substrate (RO3003, er 3.0, tan d 0.001, h 1.527 mm), 50 ohm strip width re-derived,
N = 7 and S = 0.92 unchanged. Three scales bracket the target.

| Variant | s | Board (mm) | f_res | S11 min | S11 @ 1.795 | Zin @ 1.795 | -10 dB band | Worst S11 UL 1.71-1.785 | Worst S11 DL 1.805-1.88 | Peak gain 1.71 / 1.795 / 1.88 GHz |
|---|---|---|---|---|---|---|---|---|---|---|
| s096 | 1.313 | 72.2 x 131.3 | 1.860 GHz | -19.7 dB | -13.9 dB | 39.0 - j14.4 | 1.662-1.947 GHz | -10.6 dB | -14.9 dB | 8.6 / 9.3 / 9.6 dBi |
| **s100** | **1.368** | **75.2 x 136.8** | **1.798 GHz** | **-16.6 dB** | **-16.6 dB** | **44.9 - j13.3** | **1.650-1.878 GHz** | **-11.8 dB** | **-10.1 dB** | **9.1 / 9.4 / 9.8 dBi** |
| s104 | 1.422 | 78.2 x 142.2 | 1.721 GHz | -17.8 dB | -10.9 dB | 48.9 - j29.4 | 1.536-1.803 GHz | -11.8 dB | -7.6 dB | 9.2 / 9.6 / 10.3 dBi |

Conclusions
- Resonance follows 1/s: s100 lands at 1.798 GHz for a 1.795 GHz target. Corrected scales for exactly 1.795 GHz: 1.360 / 1.370 / 1.364 (all within 0.6 % of 1.368).
- **s100 covers essentially the whole B3 band with no matching network** (worst point -10.1 dB at 1.878 GHz, i.e. no margin at the top edge). Peak gain about 9.4 dBi, end-fire (+y, Theta 90).
- s096 has the best DL match but its UL edge is -10.6 dB; s104 is too low in frequency. An intermediate s (about 1.35) would trade UL margin for DL margin: not simulated, no claim.
- Gain is HFSS GainTotal (far field); radiation efficiency was not extracted, so no efficiency is claimed.

**Caveat on labelling:** the CSV files were returned without variant labels; they were assigned to s096 / s100 / s104 from the
resonance order (smaller s = higher frequency), and s100 matches the scaling prediction within 3 MHz. If you re-run with
`run_all.ps1` the folders are labelled by construction.

## Files
| Path | Content |
|---|---|
| `specs/sXXX.yaml`, `sXXX/spec.yaml` | scaled specs |
| `sXXX/initial/hfss_build.py` | generated PyAEDT script |
| `sXXX/preview.png`, `design.json`, `RUN.md` | geometry preview, derived design, modelling assumptions |
| `sXXX/results/` | `s11.csv`, `gain.csv`, `patterns.csv` from HFSS, and `report/report.html` (S11, VSWR, Zin, gain, patterns) |
| `results_summary.txt` | one line per variant (`scripts/s11_summary.py`) |
| `run_all.ps1` | re-run the three variants |

## Re-run (Windows, HFSS Student)
```powershell
.\examples\gad_meander_b3_ro3003\run_all.ps1
```
Regenerate other bands: `py -3.12 scripts\scale_meander.py out_dir 1.795`.
