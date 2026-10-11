# PCB Yagi, FR4, LTE Band 3 (1710–1880 MHz) — simulation-ready

**Status: NOT run in HFSS** (not run for this design). Design is from a calibrated wire-MoM model; expect ±1 dB and ~±40 MHz band shift per 0.02 of the calibration constant k. The three scale variants exist to cover that.

## Target
f0 1.795 GHz, UL 1710–1785 / DL 1805–1880 MHz, FR4 (assumed εr 4.4, tanδ 0.02), 4-layer stack from TI DN034 (h10 0.226, h21 0.99, h32 0.226 mm, Cu 34.3 µm).
Structure: ground-pour reflector (all 4 layers + via wall) → driven dipole (arms on L3/L2, two-wire strip feed) → 7 directors on L3. Board 136 × 325 mm (s100).

## Method
1. Effective-medium wire MoM (NEC2/PyNEC): in-plane dims ÷ k, strips → round wires r=(w/k)/4, pour → wire grid.
2. k calibrated on TI DN034 measured directivity (7.92/8.62/9.48 dBi @ 2.40/2.44/2.48 GHz) and S11 band: **k = 0.80 ± 0.02**. Model under-predicts TI bandwidth (300 vs 497 MHz) and directivity slope.
3. Nelder-Mead + Powell on element lengths/gaps over the B3 band (`scripts/design_b3.py`), rounded to 0.05 mm (`examples/b3_yagi_n7_mom.json`).

## Predicted (k=0.80, directivity dBi / F/B dB / S11 dB, ideal 50 Ω port, no balun)
| f GHz | 1.71 | 1.795 | 1.88 |
|---|---|---|---|
| dir / F/B / S11 | 11.5 / 28 / −9.9 | 12.4 / 17 / −17.8 | 13.1 / 25 / −10.0 |

HPBW 40° (E) / 45° (H) at 1.795. Realised gain ≈ directivity − 0.5…1 dB (FR4 loss, mismatch).

Directors vs directivity (dBi @ 1.71 / 1.795 / 1.88): 3 → 9.4/10.2/10.3; 5 → 10.6/11.5/11.9; **7 → 11.5/12.4/13.1**.

## Sensitivity to k (the main risk)
| k_true | 0.76 | 0.78 | 0.80 | 0.82 | 0.84 |
|---|---|---|---|---|---|
| dir @1.795 | 13.0 | 12.7 | 12.4 | 12.1 | 11.5 |
| S11 @1.795 | −7.7 | −16.5 | −17.8 | −14.4 | −9.9 |
| band centre | high-shifted, 1.88 edge lost | | ok | | low-shifted |

Variants (all in-plane dims × s; stack and strip width unscaled): **s096** (k≈0.77), **s100** (k=0.80, baseline), **s104** (k≈0.83). Run all three; keep the one whose S11 minimum sits nearest 1.795 GHz. After the real 3D solve, re-scale in-plane dims by (f_sim/f0).

## Not covered
- Balun (unbalanced 50 Ω → two-wire) is replaced by an ideal lumped port; S11 will not match a real balun-fed board. A B3 balun must be designed separately.
- FR4 εr/tanδ vary by lot (±5 %): detune ≈ ±2.5 %. Use measured values if the fab gives them.
- No connector, solder mask, copper roughness.

## Run
```bash
pip install -e . && pip install pyaedt pywin32 ansys-pythonnet
antenna-agent run --spec examples/b3_yagi_fr4_n7_s100.yaml -b hfss -o out_s100
```
Or open the pre-generated scripts in `b3_pkg/sXXX/hfss/initial/`. Far-field saved at 1.71/1.795/1.88 GHz. Regenerate: `PYTHONPATH=. python3 scripts/make_b3_project.py out_dir`.
