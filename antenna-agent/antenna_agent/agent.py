"""Orchestrator: PDF -> spec -> (human gate) -> design -> scripts -> solve/tune -> validated report."""
from __future__ import annotations

import json
from pathlib import Path

from . import report
from .backends import available, get_backend
from .design import make_design
from .extract import extract_spec
from . import preview
from .model import build_model
from .spec import AntennaSpec, dump_spec, load_spec, missing_critical
from .tune import tune


class NeedsInput(Exception):
    """Spec incomplete: a human must edit spec.yaml and re-run with --spec."""


def run(pdf: str | None, out: str, backend: str = "mock", spec_path: str | None = None, use_llm: bool = True,
        emit_only: bool = False, max_iter: int = 6, allow_tuning: bool = True, span: float = 0.25) -> dict:
    out_p = Path(out)
    out_p.mkdir(parents=True, exist_ok=True)

    if spec_path:
        spec = load_spec(spec_path)
    elif pdf:
        spec = extract_spec(pdf, use_llm=use_llm)
    else:
        raise ValueError("need a PDF or --spec")
    dump_spec(spec, out_p / "spec.yaml")

    gaps = missing_critical(spec)
    if gaps or spec.confidence < 0.2:
        raise NeedsInput(f"Complete {out_p / 'spec.yaml'} then re-run with --spec. Problems: "
                         f"{gaps or 'extractor confidence < 0.2'}; missing: {spec.missing}")

    d = make_design(spec)
    be = get_backend(backend)
    model0 = build_model(d, span=span)
    scripts = be.emit(model0, out_p / "initial")  # always leave the as-designed scripts
    preview.render(model0, out_p / "preview.png")
    (out_p / "RUN.md").write_text(run_notes(backend, d, model0))
    if emit_only:
        (out_p / "design.json").write_text(json.dumps(dict(design=d.table(), aux=d.aux), indent=2, default=float))
        return dict(emitted=[str(s) for s in scripts], design=d.table(), warnings=d.aux.get("warnings", []))

    ok, why = available(backend)
    if not ok:
        raise RuntimeError(f"{backend} unavailable: {why}. Scripts are in {out_p / 'initial'}; run them where the "
                           f"solver is installed, or re-run with --emit-only.")
    outcome = tune(d, be, out_p / "runs", max_iter=max_iter, span=span, allow_moves=allow_tuning)
    final_scripts = be.emit(build_model(d, span=span), out_p / "final")
    return report.write_all(out_p, d, outcome, backend, final_scripts)


def run_notes(backend: str, d, m) -> str:
    warn = "\n".join(f"- {w}" for w in d.aux.get("warnings", [])) or "- none"
    cmd = {"hfss": "set AEDT_PYTHON=<python with ansys-aedt-core>   (optional: AEDT_VERSION=2025.1, AEDT_GUI=1)\n"
                   "%AEDT_PYTHON% initial/hfss_build.py out_hfss",
           "cst": "set CST_PYTHON=<python with the cst package from <CST>/Library/Python>\n"
                  "%CST_PYTHON% initial/cst_build.py out_cst\n"
                  "(or in CST: Macros > run initial/cst_build.bas)",
           "mock": "n/a"}[backend]
    f = f"{m.fmin:.3f}-{m.fmax:.3f} GHz, {m.npts} pts"
    return (f"# Run ({backend})\n\n```\n{cmd}\n```\n\nSweep {f}; fields saved at {m.fields_ghz or 'n/a'} GHz.\n"
            f"Outputs: s11.csv (f_GHz,re,im), gain.csv if far-field extraction worked (else gain_error.txt; "
            f"read the far field in the solver GUI).\n\nCompare `preview.png` with the paper's figure before solving.\n\n"
            f"## Modelling decisions to review\n{warn}\n")
