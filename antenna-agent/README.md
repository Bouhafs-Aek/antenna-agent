# antenna-agent

Antenna paper (PDF) → structured spec → closed-form design → HFSS or CST project → validated against the paper.

```
PDF ──Claude (text + figure pages)──▶ spec.yaml ──▶ [human gate if incomplete]
    ──▶ design (Balanis/Hammerstad; paper dims win) ──▶ geometry IR ──▶ hfss_build.py | cst_build.py/.bas
    ──▶ solve ──▶ S11 ──▶ tune ONLY non-paper params ──▶ report.md / design.json / s11.png
```

## Use
```bash
pip install -e .                      # numpy scipy pydantic pyyaml pymupdf anthropic matplotlib
export ANTHROPIC_API_KEY=...          # extraction; without it you get a stub spec to complete by hand

antenna-agent extract paper.pdf -o spec.yaml        # review this file: it is the only LLM-dependent step
antenna-agent run --spec spec.yaml -b hfss --emit-only -o out   # scripts only, no solver needed
antenna-agent run --spec spec.yaml -b hfss -o out               # solve + tune + report (needs AEDT)
antenna-agent run --spec spec.yaml -b cst  -o out               # needs CST + its `cst` python package
antenna-agent run paper.pdf -b mock -o out                      # plumbing test, NOT physics
```
Env: `AEDT_PYTHON` / `CST_PYTHON` (interpreter with the solver bindings), `AEDT_VERSION`, `AEDT_GUI=1`.
Exit code 2 = spec incomplete (edit `out/spec.yaml`, re-run with `--spec`).

## Rules the agent follows
- Paper-stated dimensions are used as given and never moved (`provenance: paper`). Missing ones are derived
  (`derived`); only those may be corrected by the loop (`tuned`). If everything is stated and the sim disagrees, the
  report says so rather than "fixing" the paper's geometry.
- Frequency correction: `L ← (L+2ΔL)·f_res/f0 − 2ΔL`. Match correction: from de-embedded Re(Zin),
  `Rin(0)=R/cos²(πy0/L)`, then `y0 = (L/π)·acos√(Z0/Rin(0))`.
- Validation tolerances: resonance ±2 %, S11 ≤ −10 dB, BW ±30 %.

## Scope
Families: `rect_patch` (inset-fed), `dipole`, `monopole`, `meander` (antipodal meander line, `examples/gad_meander_2p45.yaml`, DESIGN_B3_MEANDER.md), `printed_yagi` (4-layer PCB Yagi, all dims from the paper;
see `examples/ti_dn034_yagi.yaml`). Anything else (slots, arrays, PIFA, horns, fractals, metasurfaces) is rejected
(`unsupported_reason`) rather than approximated.
Yagi: the printed balun is replaced by an ideal 50 ohm lumped port on the two-wire feed, so S11 is not comparable to the
paper's; gain/directivity/pattern are. Exact balun needs the reference-design Gerber (not in the PDF).
B3 high-gain FR4 Yagi: see DESIGN.md.
Not done: connector models, conductor losses/roughness, parametric (variable-driven) projects, optimetrics.

## Status — read this
**Validated on real HFSS (Student 2025 R2, PyAEDT 1.8.0, Windows):** the antipodal meander-line end-fire antenna of
Gad & Sallam, *Sci. Rep.* 14:5769 (2024), rebuilt from the PDF with paper dimensions untouched
(`paper_replica`): band 2.155-2.695 GHz (paper: 2.2-2.7), S11 min -27.4 dB at 2.455 GHz, peak gain 9.6 dBi at 2.45 GHz,
end-fire (+y). See `results/paper_replica/` and `docs/RESULTS.md`.
**CST backend: emitted scripts only, never run.** Unit tests cover design equations, metrics, geometry IR, script syntax.
**Not solved:** the LTE B3 / FR4 adaptations are *not* matched (S11 min only about -7 to -8 dB, Zin about 20 ohm with
capacitive reactance). Pure scaling is not enough; see `docs/RESULTS.md`. Do not quote their gain: FR4 radiation
efficiency was not separately checked.

## Running HFSS from Python on Windows (Student edition)
Notes in `docs/HFSS_STUDENT_WINDOWS.md` (gRPC does not start on Student; COM mode works).
Analysis of a run: `py -3.12 scripts/analyse.py <out_hfss> --band LO HI` -> S11, VSWR, Zin, gain, polar patterns, HTML report.

## Licences and attribution
Code: MIT. The reference antenna is the work of Gad & Sallam (open access); this repo reproduces it for validation and
does not claim the design. ANSYS HFSS Student is for education/research only: check the terms before any commercial use;
results from it are not a commercial deliverable.
