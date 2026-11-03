# Same meander on FR4 (er 4.4, tan d 0.02, h 1.6 mm): paper replica and LTE B3

Step 3 of the plan: after the **replica** (RO3003, validated, `../gad_meander_replica`) and the **LTE B3 design s100** (RO3003, retained,
`../gad_meander_b3_ro3003`), the same two designs are rebuilt on cheap FR4.

Rule (guided wavelength, the paper's own): every in-plane length x s, with s = (RO3003 scale) x sqrt(eeff_RO3003 / eeff_FR4)
= (RO3003 scale) x 0.8518 (Hammerstad eeff of the 50 ohm line: 2.416 on RO3003, 3.330 on FR4). N = 7 and S = 0.92 unchanged;
the 50 ohm strip is re-derived (3.06 mm on FR4); no matching network. Three scales (x0.96, x1.00, x1.04) bracket each target.

| Case | Target | Variant | s | Board (mm) |
|---|---|---|---|---|
| replica | 2.45 GHz (paper band 2.2-2.7) | v096 / **v100** / v104 | 0.818 / 0.852 / 0.886 | 45.0x81.8 / 46.9x85.2 / 48.7x88.6 |
| b3 | 1.795 GHz (B3 1.71-1.88) | v096 / **v100** / v104 | 1.118 / 1.165 / 1.212 | 61.5x111.8 / 64.1x116.5 / 66.6x121.2 |

**Status: generated, NOT simulated. No S11 or gain is claimed.** Expect FR4 to lose gain (tan d 0.02 vs 0.001) and to shift the match:
an earlier FR4 attempt at B3 (a different scaling, kept in the git history) reached only about -8 dB. Read the radiation efficiency in the solver before quoting any gain.

## Run (Windows, HFSS Student, from the repo root)
```powershell
.\examples\gad_meander_fr4\run_fr4.ps1                  # 6 runs (replica + b3, 3 scales each)
.\examples\gad_meander_fr4\run_fr4.ps1 -Case replica    # replica only
.\examples\gad_meander_fr4\run_fr4.ps1 -Case b3 -Only v100
```
Results go to `out_fr4\<case>_<v>\` and a one-line summary per run to `my_results.txt`
(resonance, S11, Zin, -10 dB band, and the corrected scale `s_new = s * f_res / f_target`). Send the CSV files back for analysis.
