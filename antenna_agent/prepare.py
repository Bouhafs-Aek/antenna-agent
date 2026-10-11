"""PDF -> everything you need to get a spec.yaml WITHOUT an API key.

Writes: pages/page_N.png (geometry figures/tables), text.txt, spec_stub.yaml (regex stub), PROMPT.md.
Paste PROMPT.md into any LLM chat (e.g. claude.ai, with the PDF attached), save the YAML it returns as spec.yaml,
check it against the paper, then `antenna-agent run --spec spec.yaml -b hfss --emit-only`.
"""
from __future__ import annotations

import json
from pathlib import Path

from .extract import SYSTEM, geometry_pages, heuristic_spec, read_pdf, render
from .spec import dump_spec

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "gad_meander_2p45.yaml"

PROMPT = """# Task: write spec.yaml for this antenna paper

Attach the PDF (and the page images in `pages/`) to the chat, then send this prompt.

## Rules
{system}

## Output
Reply with ONE yaml block only, same keys as the example below. Put page numbers in `source_pages`.
List every dimension you could not read in `missing` (do not guess). Under `dims_mm`, only keys allowed for the family.

## Example (a correct spec for a different paper)
```yaml
{example}
```

## Allowed dims_mm keys per family
```json
{keys}
```
"""


def prepare(pdf: str | Path, out: str | Path) -> Path:
    from .spec import DIM_KEYS
    pdf, out = Path(pdf), Path(out)
    (out / "pages").mkdir(parents=True, exist_ok=True)
    doc, pages = read_pdf(pdf)
    idxs = geometry_pages(pages)
    for i, png in zip(idxs, render(doc, idxs, dpi=130)):
        (out / "pages" / f"page_{i + 1}.png").write_bytes(png)
    (out / "text.txt").write_text("\n\n".join(f"=== PAGE {i + 1} ===\n{t}" for i, t in enumerate(pages)), encoding="utf-8")
    dump_spec(heuristic_spec(pages, pdf.stem), out / "spec_stub.yaml")
    example = EXAMPLE.read_text(encoding="utf-8") if EXAMPLE.exists() else ""
    (out / "PROMPT.md").write_text(PROMPT.format(system=SYSTEM, example=example,
                                                 keys=json.dumps(DIM_KEYS, indent=1)), encoding="utf-8")
    return out
