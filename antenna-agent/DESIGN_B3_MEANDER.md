# Antipodal meander-line end-fire antenna → LTE B3 (1710–1880 MHz) — simulation-ready

Source: Gad & Sallam, *High gain antipodal meander line antenna for point-to-point WLAN/WiMAX*, Sci. Rep. 14:5769 (2024).
Original: 2.45 GHz, RO3003 (εr 3, 1.527 mm), 100 × 55 mm, N = 7, S = 0.92, S11 < −10 dB 2.2–2.7 GHz, directivity 8.13 / 9.31 / 10.9 dBi at 2.2 / 2.45 / 2.7 GHz, measured gain ≤ 10.43 dBi.

**Status: NOT run in HFSS/CST. B3 dimensions are a guided-wavelength scaling of the paper, not solver-verified.** Run `paper_replica` first.

## Adaptation rule (the paper's own: "tune by the guided wavelength")
All in-plane lengths × s, s = (2.45/1.795) · √(εeff,paper / εeff,new), εeff = Hammerstad of the 50 Ω line. N, S unchanged; stack not scaled; 50 Ω strip width re-derived (paper's 3.84 mm is reproduced for RO3003).
| variant | substrate | s | board (mm) | Wms |
|---|---|---|---|---|
| b3_meander_fr4_s100 | FR4 1.6 mm, εr 4.4, tanδ 0.02 | 1.163 | 63.9 × 116.3 | 3.0 |
| b3_meander_fr4_s096 / s104 | same | 1.116 / 1.209 | 61.4×111.6 / 66.5×120.9 | 3.0 |
| b3_meander_ro3003_s100 | RO3003 1.524 mm | 1.365 | 75.1 × 136.5 | 3.84 |
FR4 variants ±4 % cover εr spread (4.2–4.7) and the scaling approximation. Paper band 2.2–2.7 GHz maps to 1.61–1.98 GHz at nominal s; B3 sits in the middle of it.

## Expected (from the paper, mapped; not predicted by a solver here)
Directivity ≈ 8.9 dBi (1.71) → 9.3 (1.795) → 9.9 (1.88), HPBW ~50° E / ~85° H, end-fire +y (along the meander). FR4 loss will cut gain below the paper's 99 % efficiency (unknown, probably several dB at worst): read radiation efficiency in the solver. Compared with the 12.4 dBi B3 Yagi: ~3 dB less, board ~6× smaller. RO3003 variant is the low-loss reference.

## Interpretation risks (stated in design warnings)
1. Rail depth: Table 1 gives only Lr1 and S. Rails read from Fig. 11: one lower rail per radiator *pair*, outer depth e_k = S^(k−1)(Lr1+Wcon) (24.5/22.5/20.7/19.1 mm vs measured off the figure 24.7/22.2/20.8/19.1).
2. Stub: Lstub per side from the strip edge, width = strip; Pstub measured from stub left edge to right edge of radiator 1 (Fig. 6b). Stubs only match; re-tune them in the solver.
3. SMA connector not modelled; ideal lumped port at the board edge between strip and ground. Copper 35 µm and RO3003 tanδ 0.001 assumed (not in paper).
4. A wire-MoM check (as used for the Yagi) was tried and **not used**: it gave 1–3 dBi against the paper's 8–11 dBi, so it cannot be trusted for this superdirective-type array. The `paper_replica` run is the validation.

## Run order
1. `paper_replica`: expect S11 band ≈ 2.2–2.7 GHz and gain ≈ 9 dBi @ 2.45 (paper Fig. 10, 12). If not, fix the interpretation (rails/stubs) before trusting B3.
2. `b3_meander_fr4_s096/100/104`: keep the one whose S11 minimum band is centred on 1.795 GHz; then rescale in-plane dims by f_sim/1.795.
3. Far-field saved at 1.71 / 1.795 / 1.88 GHz.
Regenerate: `PYTHONPATH=. python3 scripts/make_b3_meander.py out_dir`.
