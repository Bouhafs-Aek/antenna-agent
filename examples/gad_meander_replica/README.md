# Worked example: Gad & Sallam antipodal meander antenna (PDF -> HFSS -> results)

Paper: A. Gad, M. Sallam, *High gain antipodal meander line antenna for point-to-point WLAN/WiMAX applications*,
Sci. Rep. 14:5769 (2024), open access, CC BY 4.0. Copy in `paper/` (unchanged, with attribution). RO3003, 2.45 GHz, 7 radiators.

| File | What it is |
|---|---|
| `paper/…pdf` | the source paper |
| `spec.yaml` | dimensions read from the paper (Table 1, Fig. 6), each with its page; reviewed by hand |
| `preview.png` | geometry preview to compare with the paper figure before solving |
| `hfss/hfss_build.py` | generated PyAEDT script (what HFSS runs) |
| `results/` | **real HFSS Student 2025 R2 output**: `s11.csv`, `gain.csv`, plots, `report/report.html` |
| `run.ps1` | whole pipeline in one command |

## Reproduce from the PDF
```powershell
py -3.12 -m antenna_agent prepare examples\gad_meander_replica\paper\Gad_Sallam_SciRep_14_5769_2024.pdf -o out\prep
# send PROMPT.md + the PDF to an LLM chat, save its yaml, compare with spec.yaml here, then:
.\examples\gad_meander_replica\run.ps1
```

## Results (paper dimensions untouched)
| Quantity | Paper | HFSS Student (this repo) |
|---|---|---|
| S11 < -10 dB band | 2.2-2.7 GHz | 2.155-2.695 GHz |
| S11 minimum | n/a | -27.4 dB at 2.455 GHz |
| Worst S11 in 2.2-2.7 GHz | n/a | -9.1 dB at 2.70 GHz (VSWR 2.08) |
| Zin at 2.45 GHz | n/a | 48 - j4 ohm |
| Gain at 2.2 / 2.45 / 2.7 GHz | directivity 8.13 / 9.31 / 10.9 dBi; measured gain max 10.43 dBi | 8.1 / 9.6 / 10.8 dBi (HFSS GainTotal, peak at Theta 90, Phi 90 = end-fire +y) |

Paper values are directivity (simulated) and measured gain; ours is simulated total gain, so only the trend and level are comparable.
Radiation-pattern plots need `patterns.csv`, written by the current `hfss_build.py`: run `run.ps1` once to add them.
Plots: `results/report/` (S11, VSWR, Zin, gain).
