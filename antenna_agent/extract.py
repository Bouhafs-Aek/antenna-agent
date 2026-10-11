"""PDF -> AntennaSpec. Claude reads the text plus the geometry/dimension pages as images (tables of dimensions
usually live in a figure or table caption). A regex fallback exists for offline use but only yields a stub that
must be completed by hand."""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path

import pymupdf

from .spec import DIM_KEYS, AntennaSpec, Reported, Substrate

MODEL = os.environ.get("ANTENNA_AGENT_MODEL", "claude-sonnet-5-5")
# keywords that mean the radiator is more than a single supported element (offline heuristic only)
UNSUPPORTED = ["array", "slot", "pifa", "inverted-f", "horn", "fractal", "spiral", "vivaldi",
               "metasurface", "reflectarray", "loop antenna", "helical"]
GEOM = re.compile(r"(geometry|configuration|layout|dimension|top view|side view|structure of|parameters? of)", re.I)

SYSTEM = f"""You extract an antenna specification from a research paper so it can be rebuilt in a 3D EM solver.

Rules:
- Record ONLY what the paper states. Never infer, round, or fill in typical values. If a dimension is not stated, omit it.
- Convert all lengths to millimetres. Frequencies to GHz.
- family must be one of rect_patch, dipole, monopole, printed_yagi, meander (antipodal series-dipole meander line, N radiators, scale factor S), and describes the WHOLE antenna. A Yagi is
  printed_yagi (4-layer PCB, 3 directors), NEVER dipole; arrays, slots, PIFA/IFA, horns, loops, fractals, antennas whose match depends
  on a balun or feed network are not supported either. For those set `unsupported_reason` to a short name of the
  structure (pick the nearest family only to satisfy the schema) and confidence below 0.2.
- dims_mm keys per family (use exactly these names): {json.dumps(DIM_KEYS)}
- Dimension tables often use symbols (L, W, Lg, Wg, Lf, Wf, ...). Map them carefully using the figure; if the mapping
  is ambiguous, omit the dimension and add it to `missing`.
- `reported` holds the paper's claimed results (resonance, min S11, -10 dB bandwidth, gain) for later validation only.
- source_pages: 1-based pages you used. confidence: your honest 0..1 estimate that dims_mm are mapped correctly."""


def read_pdf(path: str | Path):
    doc = pymupdf.open(str(path))
    return doc, [p.get_text("text") for p in doc]


def geometry_pages(pages: list[str], limit: int = 4) -> list[int]:
    score = [(len(GEOM.findall(t)) + 2 * len(re.findall(r"\b(table|fig\.?)\s*\d", t, re.I)) * bool(GEOM.search(t)), i)
             for i, t in enumerate(pages)]
    return sorted(i for s, i in sorted(score, reverse=True)[:limit] if s > 0)


def render(doc, idxs: list[int], dpi: int = 110) -> list[bytes]:
    return [doc[i].get_pixmap(dpi=dpi).tobytes("png") for i in idxs]


def heuristic_spec(pages: list[str], name: str) -> AntennaSpec:
    text = "\n".join(pages)
    low = text.lower()
    fam = "meander" if "meander" in low else "printed_yagi" if "yagi" in low else "rect_patch" if "patch" in low else "dipole" if "dipole" in low else "monopole" if "monopole" in low else "rect_patch"
    freqs = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*GHz", text)]
    f0 = Counter(freqs).most_common(1)[0][0] if freqs else 0.0
    er = re.search(r"(?:ε\s*r|εr|dielectric constant|permittivity)[^0-9]{0,15}(\d+(?:\.\d+)?)", text, re.I)
    h = re.search(r"(\d+(?:\.\d+)?)\s*mm[^.\n]{0,25}(?:thick|height|substrate)|(?:thickness|height)[^0-9]{0,15}(\d+(?:\.\d+)?)\s*mm",
                  text, re.I)
    hv = next((float(g) for g in (h.groups() if h else ()) if g), None)
    sub = Substrate(er=float(er.group(1)), h_mm=hv) if er and hv else None
    unsup = sorted({k for k in UNSUPPORTED if re.search(rf"\b{k}", low)})
    return AntennaSpec(name=name, family=fam, f0_ghz=f0, substrate=sub, confidence=0.1,
                       unsupported_reason=", ".join(unsup),
                       missing=["offline heuristic only: dimensions NOT extracted, complete spec.yaml by hand"],
                       notes="regex fallback (no API key or --no-llm)")


def extract_spec(pdf: str | Path, use_llm: bool = True, max_chars: int = 150_000) -> AntennaSpec:
    pdf = Path(pdf)
    doc, pages = read_pdf(pdf)
    if not use_llm or not os.environ.get("ANTHROPIC_API_KEY"):
        return heuristic_spec(pages, pdf.stem)

    import base64

    import anthropic

    client = anthropic.Anthropic()
    idxs = geometry_pages(pages)
    text = "\n\n".join(f"=== PAGE {i + 1} ===\n{t}" for i, t in enumerate(pages))[:max_chars]
    content: list[dict] = [{"type": "text", "text": f"Paper text:\n{text}"}]
    for i, png in zip(idxs, render(doc, idxs)):
        content.append({"type": "text", "text": f"Rendered page {i + 1} (figures/tables):"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                     "data": base64.b64encode(png).decode()}})
    tool = {"name": "record_antenna_spec", "description": "Record the extracted antenna specification.",
            "input_schema": AntennaSpec.model_json_schema()}
    msgs = [{"role": "user", "content": content}]
    err = None
    for _ in range(2):
        r = client.messages.create(model=MODEL, max_tokens=4096, system=SYSTEM, tools=[tool],
                                   tool_choice={"type": "tool", "name": "record_antenna_spec"}, messages=msgs)
        blk = next(b for b in r.content if b.type == "tool_use")
        try:
            spec = AntennaSpec(**blk.input)
            spec.name = spec.name or pdf.stem
            if spec.reported is None:
                spec.reported = Reported()
            return spec
        except Exception as e:  # schema violation: show the model its own error once
            err = e
            msgs += [{"role": "assistant", "content": r.content},
                     {"role": "user", "content": [{"type": "tool_result", "tool_use_id": blk.id, "is_error": True,
                                                   "content": f"Validation error, fix and call the tool again: {e}"}]}]
    raise RuntimeError(f"extraction failed schema validation twice: {err}")
