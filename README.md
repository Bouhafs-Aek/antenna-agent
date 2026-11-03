# antenna-agent

Turn an antenna paper (PDF) into a **simulation-ready ANSYS HFSS project** on a Windows PC with **HFSS Student**, then check
the result against the paper. **No API key, no internet needed at run time**: Claude (or any chat LLM) reads the PDF and gives you a
`spec.yaml`; the code builds the geometry, the HFSS script and the analysis plots.

This repo follows one plan on one antenna family, **the Gad & Sallam antipodal meander end-fire antenna**:
1. **Paper replica** on RO3003 - done, validated against the paper (`examples/gad_meander_replica/`).
2. **LTE B3 adaptation** on RO3003, same geometry scaled, no matching network - done, **s100 is the retained design** (`examples/gad_meander_b3_ro3003/`).
3. **Both again on FR4** (er 4.4, h 1.6 mm) - generated, to simulate (`examples/gad_meander_fr4/`).

```
paper.pdf --(Claude)--> spec.yaml --> design --> geometry --> hfss_build.py --> HFSS Student --> s11/gain/patterns.csv --> report
```

## Results (HFSS Student 2025 R2, PyAEDT 1.8, Windows)
| Design | Result |
|---|---|
| **Replica** of Gad & Sallam, Sci. Rep. 14:5769 (2024), RO3003, paper dimensions untouched | -10 dB band 2.155-2.695 GHz (paper 2.2-2.7), S11 min **-27.4 dB at 2.455 GHz**, Zin 48 - j4 ohm, gain 8.1 / 9.6 / 10.8 dBi at 2.2 / 2.45 / 2.7 GHz, end-fire |
| **LTE B3**, same geometry x 1.368, same RO3003, **no matching network** (`s100`, board 75.2 x 136.8 mm) | f_res **1.798 GHz**, S11 min **-16.6 dB**, Zin 45 - j13 ohm, -10 dB band **1.650-1.878 GHz** (covers B3, worst -10.1 dB at 1.878 GHz), gain 9.1 / 9.4 / 9.8 dBi at 1.71 / 1.795 / 1.88 GHz |

Full tables: `docs/RESULTS.md`, `examples/gad_meander_replica/`, `examples/gad_meander_b3_ro3003/` (CSV files and HTML reports included).
Not done: fabrication/measurement, radiation efficiency, connector/housing effects. Credit for the reference design: Gad & Sallam
(`docs/REFERENCE.md`). Code: MIT. **HFSS Student is for education/research only.**

## 1. Install (Windows 10/11)
Needs ANSYS Electronics Desktop **Student 2025 R2** (default path `C:\Program Files\ANSYS Inc\ANSYS Student\v252\AnsysEM`), Python **3.12** and Git.
```powershell
git clone https://github.com/Bouhafs-Aek/antenna-agent.git
cd antenna-agent
py -3.12 -m pip install -e .
py -3.12 -m pip install pyaedt pywin32 ansys-pythonnet
```
Always use `py -3.12 -m pip` (a bare `pip` may belong to another Python).

## 2. Run the examples (no PDF needed)
Replica of the paper (a few minutes in HFSS):
```powershell
.\examples\gad_meander_replica\run.ps1
```
LTE B3 on RO3003 (s096 / s100 / s104, results already included; **s100 is the retained design**; `-Force` re-simulates):
```powershell
.\examples\gad_meander_b3_ro3003\run_all.ps1 -Force
```
FR4 versions (replica + B3, three scales each, not simulated yet):
```powershell
.\examples\gad_meander_fr4\run_fr4.ps1
```
Each run writes `s11.csv`, `gain.csv`, `patterns.csv`, `antenna.aedt` and `report\report.html` (S11, VSWR, Zin, gain, patterns).
Reading guide: S11 below -10 dB (VSWR < 2) is the usable band; end-fire means the gain peak is at Theta 90, Phi 90 (+y).

## 3. Use a paper PDF with Claude (no API key)
Full guide: **`docs/USE_WITH_CLAUDE.md`**. Short version:
1. `py -3.12 -m antenna_agent prepare paper.pdf -o out\prep` writes `PROMPT.md` and `pages\page_N.png`.
2. In a Claude chat, attach the PDF and the page images, paste `PROMPT.md`. Claude returns a yaml; save it as `my_spec.yaml`.
3. **Check every dimension against the paper** (the only step that can go wrong silently).
4. `py -3.12 -m antenna_agent run --spec my_spec.yaml -b hfss --emit-only -o out\my_paper`; compare `out\my_paper\preview.png` with the paper's figure.
5. Simulate (section 4) and analyse (section 5). Send `s11.csv` / `gain.csv` back to Claude to read them (name which variant they belong to).

Supported families: `meander` (validated), `rect_patch`, `dipole`, `monopole`, `printed_yagi`, `ifa_meander` (generated, not validated here). Anything else is rejected instead of approximated.

## 4. Run HFSS Student by hand
HFSS Student does not start in PyAEDT's default gRPC mode: use **COM mode** (`docs/HFSS_STUDENT_WINDOWS.md`).
```powershell
$env:ANSYSEMSV_ROOT252="C:\Program Files\ANSYS Inc\ANSYS Student\v252\AnsysEM"
$env:AEDT_VERSION="2025.2"; $env:AEDT_STUDENT="1"; $env:AEDT_GUI="1"; $env:AEDT_COM="1"
cd out\my_paper\initial
py -3.12 -u hfss_build.py ..\out_hfss 2>&1 | Tee-Object -FilePath ..\run_log.txt
```
Close HFSS first (politely, not `Stop-Process`). If it fails or hangs at "COM table not readable", see Troubleshooting.

## 5. Analyse
```powershell
py -3.12 -m pip install numpy matplotlib
py -3.12 scripts\analyse.py out\my_paper\out_hfss --band LO HI     # report\report.html + PNGs
py -3.12 scripts\s11_summary.py out\my_paper\out_hfss myrun 1.3677 1.795   # one line: f_res, band, Z, corrected scale
```
Shifting a band: resonance goes as 1/s, so `s_new = s * f_res / f_target`. `py -3.12 scripts\scale_meander.py out_dir 1.795` regenerates the scaled specs.

## Troubleshooting (HFSS Student on Windows)
| Symptom | Fix |
|---|---|
| `Project is locked` | close HFSS, delete `*.lock` in the output folder |
| `IndexError` at start, or `com_error ... EnumRunning`, or stuck at "COM table not readable" | killed HFSS/Python sessions fill the Windows COM table: close HFSS normally, `Get-Process ansysedt*,python* \| Stop-Process`, then **sign out of Windows and back in** (no reboot needed) |
| Python exit code -1073741819 (0xC0000005) at import | broken compiled libs: `py -3.12 -m pip install --force-reinstall numpy scipy matplotlib`; or run `hfss_build.py` directly (it needs only pyaedt) |
| Old CSV files reappear | delete the output folder before re-running; scripts here delete stale `s11.csv` |

## Rules the agent follows
- Dimensions stated in the paper are never moved; missing ones are derived and flagged in `RUN.md`.
- Validation tolerances: resonance within 2 %, S11 at most -10 dB, bandwidth within 30 %.
- Validate every new extraction on a paper whose result is known (a far-field slicing bug was found this way).

## Tests
```powershell
py -3.12 -m pip install pytest
py -3.12 -m pytest -q tests
```
