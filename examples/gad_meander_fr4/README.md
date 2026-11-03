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

## Run (Windows, HFSS Student, from the repo root)
```powershell
.\examples\gad_meander_fr4\run_fr4.ps1                  # 6 runs (replica + b3, 3 scales each)
.\examples\gad_meander_fr4\run_fr4.ps1 -Case replica    # replica only
.\examples\gad_meander_fr4\run_fr4.ps1 -Case b3 -Only v100
```
Results go to `out_fr4\<case>_<v>\`, one summary line per run to `my_results.txt`
(resonance, S11, Zin, -10 dB band, corrected scale `s_new = s * f_res / f_target`). Send the CSV files back, naming the case.
