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

## Iteration 2 (generated, NOT simulated except where stated): s = 0.925 x RO3003 scale, three scales each
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

## FR4 replica, s = 0.925 (`replica/v100`, simulated; summary numbers from the run log, CSV not archived)
f_res 2.492 GHz (+1.7 % vs 2.45), S11 min -10.5 dB at 2.490 GHz, S11(2.45) = -9.7 dB, Zin(2.45) = 28 - j13 ohm, -10 dB band 2.460-2.520 GHz (60 MHz),
worst S11 in 2.2-2.7 GHz -4.3 dB (at 2.7), max VSWR 4.14. Gain (HFSS, realised) at 2.2 / 2.45 / 2.7 GHz: 5.9 (4.8) / 8.8 (8.3) / 8.3 (6.3) dBi, beamwidth -3 dB at 2.45 GHz 82 deg (YZ) / 56 deg (XY).
Reading: the scale 0.925 brings the resonance to within 1.7 % of the target (pure frequency correction would be s = 0.9407), but like the FR4 B3 the impedance is not 50 ohm (28 - j13),
so the paper's 2.2-2.7 GHz band is not covered; a matching section (as for `b3_matched`) is needed. Gain 0.8 dB below the RO3003 replica at 2.45 GHz (9.6 dBi).

### FR4 replica with matching sections: `replica_matched` (SIMULATED, final)
`antenna-agent match` on the real `replica/v100/results/s11.csv`, band 2.2-2.7 GHz, sections limited to 30 mm: port side Zt 30 ohm (W 6.58 mm, L 7.15 mm), radiator side Zt 90 ohm (W 0.93 mm, L 5.91 mm);
feed, board and ground lengthened by 13.06 mm. Predicted worst S11 over 2.2-2.7 GHz: **-4.3 -> -11.3 dB** (ideal lines; HFSS decides, as for `b3_matched`). Run: `.\examples\gad_meander_fr4\run_fr4.ps1 -Case replica_matched`.
**HFSS result (summary numbers from the run log, CSV not archived):** S11 min -16.2 dB at 2.285 GHz, **-10 dB band 2.170-2.690 GHz (520 MHz, vs 60 MHz unmatched)**, worst S11 in 2.2-2.7 GHz -8.7 dB (at 2.7 GHz; predicted -11.3), max VSWR 2.15, Zin(2.45) = 65 - j22 ohm.
Gain (HFSS, realised) at 2.2 / 2.45 / 2.7 GHz: 6.4 (6.1) / 8.6 (8.4) / 7.5 (6.9) dBi; beamwidth -3 dB at 2.45 GHz 82 deg (YZ) / 56 deg (XY). The paper's band 2.2-2.7 GHz is covered at -10 dB up to 2.69 GHz; the minimum moved down to 2.285 GHz
(the sections shift the match), the 2.7 GHz edge is at -8.7 dB. Gain 1.0 dB below the RO3003 replica at 2.45 GHz (9.6 dBi). Not retained for further iteration.

## FR4 B3 with matching sections: `b3_matched` (FINAL, simulated)
Two series microstrip sections on the feed, designed by `antenna-agent match` from the unmatched S11 above (ideal lines): port side Zt 31.5 ohm (W 6.16 mm, L 20.25 mm),
radiator side Zt 90 ohm (W 0.93 mm, L 4.75 mm); feed, board and ground lengthened by the sections (board 69.6 x 151.5 mm). Real HFSS results in `b3_matched/v100/results/`
(file labels were not attached: assigned from the run order).
| Quantity | Result |
|---|---|
| S11 min | **-24.0 dB at 1.755 GHz** (target 1.795, -2.2 %) |
| -10 dB band | **1.668-2.004 GHz (336 MHz)**, covers all of B3 (1.71-1.88) |
| -15 dB band | 1.704-1.890 GHz |
| S11 at 1.71 / 1.795 / 1.88 GHz | -16.2 / -21.8 / -16.7 dB |
| Zin at 1.71 / 1.795 / 1.88 GHz | 52+j16 / 51-j8 / 57-j14 ohm |
| Gain (HFSS GainTotal) at 1.71 / 1.795 / 1.88 GHz | 7.7 / 8.4 / 8.6 dBi (RO3003 design: 9.1 / 9.4 / 9.8); no efficiency claimed |
Margin to the B3 band edges: 42 MHz on the low side, 124 MHz on the high side.
Iteration 1 of this case failed because of a generator bug (the sections replaced the feed instead of being added): data kept in `b3_matched/iter1_sections_replaced/results/`.

## FR4 B3 frequency-corrected: `b3_final` (simulated, NOT retained)
`b3_matched` with every in-plane length x 0.9777 (= 1.755/1.795) to centre the minimum. Real results in `b3_final/v100/results/`:
S11 min -21.0 dB at 1.806 GHz, -10 dB band 1.692-1.911 GHz (221 MHz), S11 at 1.71 / 1.795 / 1.88 = -11.5 / -20.8 / -13.4 dB, gain 7.7 / 8.2 / 8.3 dBi.
The minimum is centred (+0.6 %) but the band shrank by 115 MHz (the section widths scaled too, so their impedances moved) and the low edge has only 18 MHz of margin.
Not retained: `b3_matched` has more margin against the FR4 er spread (4.2-4.7, about +-40 MHz).

## SMA connector: removed
A coax/SMA wave-port model was tried in HFSS Student. After fixing the port (it needs a PEC back-stop), it solved but gave |S11| = 0.998 over the whole band (no power reaches the antenna),
so it was abandoned and the cases were deleted. The final design is simulated with the ideal 50 ohm port at the board edge. The SMA is a fabrication detail:
use a standard PCB edge-launch SMA for a 1.6 mm board and take the footprint from its datasheet (its discontinuity at 1.8 GHz is small compared with the 42 MHz low-side margin, but it is not simulated).

## Status of every case
| Case | Substrate | Status |
|---|---|---|
| `../gad_meander_replica` | RO3003 | simulated, validated (S11 min -27.4 dB at 2.455 GHz) |
| `../gad_meander_b3_ro3003/s100` | RO3003 | simulated, RETAINED B3 (f_res 1.798 GHz, -10 dB band 1.650-1.878 GHz, 9.1 / 9.4 / 9.8 dBi) |
| `replica/iter1_lambda_g` | FR4 | simulated, mistuned (f_res 2.661 GHz) |
| `replica/v100` | FR4 | simulated: f_res 2.492 GHz, S11 min -10.5 dB, band 2.460-2.520 GHz, Zin 28-j13 ohm (unmatched) |
| `replica_matched/v100` | FR4 | simulated: -10 dB band 2.170-2.690 GHz (520 MHz), S11 min -16.2 dB at 2.285 GHz, worst S11 -8.7 dB at 2.7 GHz |
| `replica/v096, v104` | FR4 | generated, not simulated |
| `b3/v100` | FR4 | simulated, no -10 dB band (unmatched) |
| `b3/v096, v104` | FR4 | generated, not simulated |
| **`b3_matched/v100`** | FR4 | **simulated: the design to fabricate** |
| `b3_final/v100` | FR4 | simulated, not retained |

## Fabrication files (`b3_matched/fabrication/`)
Generated from the same geometry HFSS solves (`python scripts/export_fab.py examples/gad_meander_fr4/b3_matched/specs/v100.yaml <out>`): `top_copper.gtl`, `bottom_copper.gbl` (as seen from the top, not mirrored), `outline.gko` (Gerber RS-274X, mm), `board.dxf`, `preview.png`, `fab_sheet.txt` (board 69.58 x 151.51 mm, every copper rectangle).
The copper count matches HFSS (18 top + 16 bottom objects). Missing: SMA footprint/pads, solder mask, silkscreen, holes: add them from the connector datasheet before ordering, and view the Gerbers in a viewer first.

KiCad version: `b3_matched/fabrication/kicad/` (`python scripts/export_kicad.py <spec> <out> b3_matched`, needs `pip install shapely`): `b3_matched.kicad_pcb` (copper as polygons on F.Cu/B.Cu, board outline on Edge.Cuts, connector edge at the bottom),
and Gerber X2 files named like KiCad's (`-F_Cu.gbr`, `-B_Cu.gbr`, `-Edge_Cuts.gbr`). Checked: the Gerber copper areas equal the model's copper (1701.1 mm2 top, 4391.7 mm2 bottom). Not opened in KiCad itself (not available here): open the .kicad_pcb, place the SMA footprint on the bottom edge, run DRC, plot.

## Path to fabrication
1. Fabricate `b3_matched`: FR4 1.6 mm, 35 um copper, double sided, finish ENIG or HASL, strip width tolerance +-0.05 mm. Ask the fab for the real er of its FR4 (4.2-4.7 moves the resonance by a few %).
2. Choose the PCB edge-launch SMA, take the footprint from the datasheet, keep the 50 ohm strip (3.06 mm) up to the pad.
3. Export Gerber (top copper, bottom copper, outline, drill) from the geometry; order 3 boards.
4. Measure S11 with a VNA calibrated at the SMA plane over 1.5-2.1 GHz. If the minimum is off, correct with `s_new = s * f_res / 1.795`, but expect the band to change (see `b3_final`).
5. Not done: radiation efficiency, a real connector model, tolerance study on er.

## Run (Windows, HFSS Student, from the repo root; sign out of Windows between runs)
```powershell
.\examples\gad_meander_fr4\run_fr4.ps1 -Case b3_matched   # the retained FR4 B3 design
.\examples\gad_meander_fr4\run_fr4.ps1 -Case b3_final
.\examples\gad_meander_fr4\run_fr4.ps1 -Case replica     # replica only
.\examples\gad_meander_fr4\run_fr4.ps1 -Case b3 -Only v100
```
Results go to `out_fr4\<case>_<v>\`, one summary line per run to `my_results.txt`. Each HFSS run leaves COM entries in Windows: after a run, sign out/in before the next one, otherwise the next attach hangs.
