# Same meander on FR4 (er 4.4, tan d 0.02, h 1.6 mm): paper replica and LTE B3

Step 3 of the plan, after the **replica** (RO3003, validated, `../gad_meander_replica`) and the **LTE B3 design s100** (RO3003, retained,
`../gad_meander_b3_ro3003`): the same two designs rebuilt on cheap FR4. All in-plane lengths x s, N = 7 and S = 0.92 unchanged,
50 ohm strip re-derived (3.06 mm), no matching network.

## Iteration 1 (simulated): guided-wavelength guess s = 0.852 - mistuned
`replica/iter1_lambda_g/` (spec + real HFSS results). s = sqrt(eeff_RO3003/eeff_FR4) = 0.852 from the 50 ohm line permittivities.
| Quantity | Result (replica on FR4, s = 0.852) |
|---|---|
| f_res | **2.661 GHz** (target 2.45) |
| S11 min | -11.2 dB at 2.66 GHz |
| S11 at 2.2 / 2.45 / 2.7 GHz | -3.9 / -5.4 / -10.3 dB |
| Zin at 2.45 GHz | 22 - j31 ohm |
| -10 dB band | 2.620-2.705 GHz only |
| Gain at 2.2 / 2.45 / 2.7 GHz | 4.5 / 7.8 / 9.2 dBi (RO3003 replica: 8.1 / 9.6 / 10.8) |
Reading: the line-based rule over-shrinks the antenna: the structure's effective permittivity rises less than the 50 ohm line's
(about x1.17 instead of x1.38). Corrected scale for 2.45 GHz: s = 0.852 x 2.661 / 2.45 = **0.925** (resonance goes as 1/s).
This assumes the file set was the central case (v100) of the first batch; the CSV files carried no label.

## Iteration 2 (generated, NOT simulated): s = 0.925 x RO3003 scale, three scales each
| Case | Target | Variant | s | Board (mm) |
|---|---|---|---|---|
| replica | 2.45 GHz (paper band 2.2-2.7) | v096 / **v100** / v104 | 0.888 / 0.925 / 0.962 | 48.8x88.8 / 50.9x92.5 / 52.9x96.2 |
| b3 | 1.795 GHz (B3 1.71-1.88) | v096 / **v100** / v104 | 1.215 / 1.265 / 1.316 | 66.8x121.5 / 69.6x126.5 / 72.4x131.6 |
The B3 case uses the same factor 0.925 on the B3 RO3003 scale 1.368 (one data point, extrapolated to another band: expect a few % error).
No S11 or gain is claimed for iteration 2. Expect a narrower band and a lower gain than on RO3003 (tan d 0.02), and check radiation efficiency before quoting any gain.

## FR4 B3, ideal port, no matching (`b3/v100`, simulated)
Real HFSS results in `b3/v100/results/` (assumed to be the central scale 1.265: the CSV files carried no label).
| Quantity | Result |
|---|---|
| f_res | 1.823 GHz (target 1.795, +1.6 %) |
| S11 min | -7.8 dB; **no -10 dB band** |
| S11 at 1.71 / 1.795 / 1.88 GHz | -4.9 / -7.3 / -6.1 dB (worst -4.9 dB at 1.71) |
| Zin at 1.795 GHz | 23.2 - j18.4 ohm |
| Gain at 1.71 / 1.795 / 1.88 GHz | 8.0 / 8.8 / 9.0 dBi (realised, mismatch included: 6.3 / 7.9 / 7.8) |
Not matched: the radiation is fine (gain only about 0.6 dB below the RO3003 design, 9.1 / 9.4 / 9.8), the impedance is not.
This is the same behaviour as the FR4 replica (Zin 29 - j25 ohm): FR4 shifts the impedance and scaling alone does not restore 50 ohm.

## FR4 B3 with matching sections (`b3_matched`)
Two series microstrip sections on the feed, designed by `antenna-agent match` from the unmatched S11 above (ideal lines, discontinuities and coupling ignored):
port side Zt 31.5 ohm (W 6.16 mm, L 20.25 mm), radiator side Zt 90 ohm (W 0.93 mm, L 4.75 mm). Predicted worst S11 over 1.71-1.88 GHz: **-4.9 -> -16.5 dB**.

**Iteration 1 (simulated, FAILED - my generator bug).** `b3_matched/iter1_sections_replaced/results/`: f_res 1.989 GHz, S11 in B3 only -2.3 / -3.4 / -7.5 dB
(1.71 / 1.795 / 1.88 GHz), Zin 9.5 - j0.6 ohm at 1.795, realised gain 3.7 / 5.9 / 8.1 dBi. Cause: the generated board **replaced** the first 25 mm of the 50 ohm feed by the
sections, while the prediction assumes they are **added** in series before the original feed. A transmission-line model of the replaced circuit gives -1.7 / -2.3 / -2.0 dB
and a low-impedance load (5-7 - j11..14 ohm), the same behaviour as the HFSS result, while the "added" circuit gives -16.5 / -16.8 / -28 dB: the model is usable, the geometry was wrong.
**Iteration 2 (generated, NOT simulated; `b3_matched/v100`).** `match` now lengthens the feed (Lms), the board (Bl) and the ground (Gnd) by the sections' total length (25 mm),
so the original feed and stub keep their position relative to the radiator: board 69.6 x 151.5 mm. The prediction is still an ideal-line estimate; HFSS decides.

## B3 on FR4 with the SMA connector (`b3_sma/`, generated, NOT simulated)
Same three B3 scales (1.215 / 1.265 / 1.316), now fed through an SMA end-launch (48.9 ohm coax, pin 1.27 mm, PTFE 4.1 mm, shell 6.35 mm,
wave port 6 mm outside the board edge) instead of the ideal lumped port. This is the version that goes to fabrication, because the
connector shifts the match. Generic SMA dimensions, **not a specific part**; never solved in HFSS Student before: if the script stops with
"coax wave port failed", send `out_fr4\run_log_b3_sma_v100.txt`; if Student refuses the mesh (about 128k elements), shorten `out_mm`/`free_mm` in the spec.
The ideal-port `b3/` cases are only a calibration step: run `b3_sma` directly to save time, and `b3` only if `b3_sma` misbehaves.

## Path to fabrication (after the simulation)
1. Simulate `b3_sma` (3 scales). Pick the scale whose -10 dB band covers 1.71-1.88 GHz; correct with `s_new = s * f_res / 1.795`, re-simulate once.
2. Check radiation efficiency / gain in HFSS: FR4 (tan d 0.02) costs gain; decide if the loss is acceptable.
3. Choose the real SMA part (PCB end-launch for 1.6 mm board), take its footprint from the datasheet (pad, ground tabs, clearance), put that footprint in the model, re-simulate.
4. Board order: FR4 1.6 mm, 35 um copper, double sided, finish ENIG or HASL, controlled strip width +-0.05 mm; ask the fab for the real er (FR4 is 4.2-4.7, which moves the resonance by a few %).
5. Export Gerber (top copper, bottom copper, outline, drill) from the final geometry; order 3 boards (the three scales or +-2 % around the best one).
6. Measure S11 with a VNA (calibrated at the SMA plane) and compare with the simulation; trim the stub if the resonance is off.
Steps 3 and 5 need the final connector choice: not done yet.

## Run (Windows, HFSS Student, from the repo root)
```powershell
.\examples\gad_meander_fr4\run_fr4.ps1 -Case b3_sma    # B3 with the SMA connector (3 runs): do this next
.\examples\gad_meander_fr4\run_fr4.ps1                  # all cases (9 runs)
.\examples\gad_meander_fr4\run_fr4.ps1 -Case replica    # replica only
.\examples\gad_meander_fr4\run_fr4.ps1 -Case b3 -Only v100
```
Results go to `out_fr4\<case>_<v>\`, one summary line per run to `my_results.txt`
(resonance, S11, Zin, -10 dB band, corrected scale `s_new = s * f_res / f_target`). Send the CSV files back, naming the case.


## Iteration 2 result and next step
`b3_matched` (HFSS, FR4): S11 min -24.0 dB at 1.755 GHz, -10 dB band 1.668-2.004 GHz (covers B3 1.71-1.88), gain 7.7/8.4/8.6 dBi. Next: `-Case b3_final` (all lengths x0.9777 to centre on 1.795 GHz, ideal port), then `-Case b3_final_sma` (same + SMA coax port; first time solved in HFSS Student, may hit the mesh limit).
