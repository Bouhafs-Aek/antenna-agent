# antenna-agent

Turn an antenna paper (PDF) into a **simulation-ready ANSYS HFSS project**, then check the result against the paper.
Runs on a Windows PC with **ANSYS HFSS Student**. **No API key and no internet needed**: you give the agent a
`spec.yaml` (the paper's dimensions, written by you or by any LLM chat from the PDF) and it builds the geometry, the HFSS script,
and the analysis plots.

```
PDF ──▶ spec.yaml (from the paper's dimensions) ──▶ design (paper dimensions win) ──▶ geometry ──▶ hfss_build.py ──▶ HFSS solve
          ──▶ s11.csv / gain.csv / patterns.csv ──▶ analyse.py ──▶ report.html (S11, VSWR, Zin, gain, patterns)
```

## Status (honest)
- **Validated on real HFSS Student 2025 R2** (PyAEDT 1.8, Windows): Gad & Sallam antipodal meander end-fire antenna,
  *Sci. Rep.* 14:5769 (2024), paper dimensions untouched. Band 2.155-2.695 GHz (paper 2.2-2.7), S11 min -27.4 dB at
  2.455 GHz, 9.6 dBi at 2.45 GHz, end-fire. See `examples/gad_meander_replica/` (paper PDF, spec, script, real results).
- **LTE B3 / FR4 adaptation: not matched** (S11 min about -8 dB, Zin about 20 ohm). See `docs/RESULTS.md` and `examples/gad_meander_b3_fr4/`.
- Reference design credit: Gad & Sallam. Code: MIT. **HFSS Student is for education/research only.**

## Worked examples (with real results)
- `examples/gad_meander_replica/`: paper PDF -> spec -> HFSS script -> S11, VSWR, Zin, gain plots, `run.ps1`.
- `examples/gad_meander_b3_fr4/`: LTE B3 adaptation on FR4 (negative result, kept on purpose).

## 1. Requirements (Windows 10/11)
- ANSYS Electronics Desktop **Student** 2025 R2 installed (default path `C:\Program Files\ANSYS Inc\ANSYS Student\v252\AnsysEM`).
- Python **3.12** (`py -3.12 --version`) and Git.

```powershell
git clone https://github.com/Bouhafs-Aek/antenna-agent.git
cd antenna-agent
py -3.12 -m pip install -e .
py -3.12 -m pip install pyaedt pywin32 ansys-pythonnet
```
`pyaedt`, `pywin32`, `ansys-pythonnet` are required for HFSS. The `anthropic` package is **not** needed.

## 2. Generate the HFSS project (no solver, no key)
```powershell
py -3.12 -m antenna_agent run --spec examples\gad_meander_2p45.yaml -b hfss --emit-only -o out\paper_replica
```
Creates `out\paper_replica\` with `initial\hfss_build.py`, `preview.png` (compare with the paper figure),
`design.json`, `spec.yaml` and `RUN.md` (modelling assumptions to review).

Other ready specs are in `examples\` (LTE B3 and B40 meander variants, FR4 patch, printed Yagi).
Batch of meander variants: `py -3.12 scripts\make_b3_meander.py out_dir [b3|b40]`.

## 3. Run HFSS Student
HFSS Student does not start in PyAEDT's default gRPC mode, so use **COM mode** (details in `docs\HFSS_STUDENT_WINDOWS.md`):
```powershell
$env:ANSYSEMSV_ROOT252="C:\Program Files\ANSYS Inc\ANSYS Student\v252\AnsysEM"
$env:AEDT_VERSION="2025.2"; $env:AEDT_STUDENT="1"; $env:AEDT_GUI="1"; $env:AEDT_COM="1"
cd out\paper_replica\initial
py -3.12 hfss_build.py ..\out_hfss 2>&1 | Tee-Object -FilePath ..\run_log.txt
```
HFSS opens, builds the model, solves (a few minutes), and writes into `out_hfss\`:
`s11.csv`, `gain.csv`, `patterns.csv`, and `antenna.aedt` (open it in HFSS to inspect; the script creates no HFSS report plots, use `analyse.py`).
Close any running HFSS first: `Get-Process ansysedt*, ansyscl* | Stop-Process -Force`.

## 4. Analyse
```powershell
py -3.12 -m pip install numpy matplotlib
py -3.12 scripts\analyse.py out\paper_replica\out_hfss --band 2.2 2.7
```
Writes `out_hfss\report\report.html` plus PNGs: S11 (dB), VSWR, R/X of Zin, gain (total and realised with mismatch),
polar patterns (YZ and XY planes, half-power beamwidth), Theta-Phi map, and a summary table.
Reading guide: S11 below -10 dB (VSWR below 2) is the usable band; end-fire here means the peak is at Theta 90, Phi 90 (+y).

## 5. Use your own paper (PDF), no API key
```powershell
py -3.12 -m antenna_agent prepare paper.pdf -o out\my_paper_prep
```
This writes `PROMPT.md` (extraction rules + example + allowed dimension names), `pages\page_N.png` (the figure/table pages),
`text.txt` and `spec_stub.yaml`. Then:
1. Open any LLM chat (for example claude.ai), attach the PDF (and the page images), paste `PROMPT.md`.
2. Save the YAML it returns as `my_spec.yaml`. **Check every dimension against the paper's table and figure**: this is the only step that can go wrong silently.
3. `py -3.12 -m antenna_agent run --spec my_spec.yaml -b hfss --emit-only -o out\my_paper`, compare `preview.png` with the paper figure, then steps 3-4.

Families: `rect_patch`, `dipole`, `monopole`, `meander`, `printed_yagi`. Anything else (arrays, slots, PIFA, horns...) is rejected instead of approximated.
Optional with an Anthropic key instead of the chat: `py -3.12 -m pip install anthropic`, set `ANTHROPIC_API_KEY`,
`py -3.12 -m antenna_agent extract paper.pdf -o spec.yaml`, then review it the same way.

## Rules the agent follows
- Dimensions stated in the paper are never moved. Missing ones are derived; only derived ones may be tuned.
  If everything is stated and the simulation disagrees, the report says so.
- Validation tolerances: resonance within 2 %, S11 at most -10 dB, bandwidth within 30 %.
- Always validate a new extraction or geometry on a paper whose result is known (that is how a gain-array slicing
  bug was found: -7 dBi reported for a 9.6 dBi antenna).

## Student-edition limits
Mesh of about 128k elements, education/research licence, no commercial deliverables. Connector models, conductor
roughness and optimetrics are not modelled. Solver: HFSS only.

## Tests
```powershell
py -3.12 -m pip install pytest
py -3.12 -m pytest -q tests
```
