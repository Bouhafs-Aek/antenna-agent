# Using a paper PDF with Claude (no API key)

The agent never calls an AI itself. Claude (or any chat LLM) does the one step that needs reading: **PDF -> `spec.yaml`**.
Everything after that (geometry, HFSS script, simulation, analysis) is deterministic code on your PC.

```
paper.pdf --prepare--> PROMPT.md + pages/*.png --Claude--> spec.yaml --(you check)--> run --emit-only --> hfss_build.py --> HFSS --> analyse
```

## A. Claude in the browser or desktop app (claude.ai)
1. On your PC: `py -3.12 -m antenna_agent prepare paper.pdf -o out\prep`
   writes `out\prep\PROMPT.md`, `pages\page_N.png` (pages with figures/tables), `text.txt`, `spec_stub.yaml`.
2. Open a new Claude chat. Attach **paper.pdf** and the **pages\page_*.png** of the geometry figure and the dimension table.
3. Paste the whole content of `PROMPT.md` and send.
4. Claude answers with ONE yaml block. Save it as `my_spec.yaml`.
5. **Check it yourself against the paper** (this is the only step that can fail silently):
   - every number in `dims_mm` equals the paper's table/figure (units mm), including the substrate (`er`, `tan_d`, `h_mm`);
   - `family` is right (supported: `meander`, `rect_patch`, `dipole`, `monopole`, `printed_yagi`, `ifa_meander`; the validated one is `meander`);
   - anything Claude could not read is listed in `missing`, not guessed. Fill it in or accept a derived value consciously.
6. `py -3.12 -m antenna_agent run --spec my_spec.yaml -b hfss --emit-only -o out\my_paper`
   then open `out\my_paper\preview.png` and compare it with the paper's figure **before** simulating.

## B. Claude Code (or Claude with your folder connected)
Open the repo folder in Claude, put the PDF in it, and ask:

> Read `paper.pdf`. Follow `antenna_agent/prepare.py` (run `py -3.12 -m antenna_agent prepare paper.pdf -o out\prep`, then use `out\prep\PROMPT.md`).
> Write `my_spec.yaml`, then run `py -3.12 -m antenna_agent run --spec my_spec.yaml -b hfss --emit-only -o out\my_paper`.
> List every dimension you were not sure about.

Claude writes the spec and generates the project. You still compare `preview.png` with the paper and review `RUN.md`.

## C. After the HFSS run: let Claude read the results
Attach `s11.csv`, `gain.csv` (and `patterns.csv`) from `out_hfss\` to a chat, and say which variant/scale they belong to
**(name the files per variant: the CSVs carry no label)**. Ask: "resonance, -10 dB band, impedance at f0, gain, and the scale
correction". The rule is `s_new = s * f_res / f_target` (resonance goes as 1/s). Or do it locally:
`py -3.12 scripts\s11_summary.py out_hfss myrun 1.3677 1.795`.

## Rules that keep it honest
- Dimensions stated in the paper are never moved; missing ones are derived and flagged.
- Never trust a new extraction before it reproduces the paper's own result (see `examples/gad_meander_replica/`).
- A number that is not in an HFSS output file is not a result.
