from __future__ import annotations

import argparse
import json
import sys

from .agent import NeedsInput, run
from .extract import extract_spec
from .prepare import prepare
from .simulate import simulate
from .spec import dump_spec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="antenna-agent", description="Antenna paper (PDF) -> HFSS project")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract", help="PDF -> spec.yaml only")
    e.add_argument("pdf")
    e.add_argument("-o", "--out", default="spec.yaml")
    e.add_argument("--no-llm", action="store_true")

    p = sub.add_parser("prepare", help="PDF -> page images + PROMPT.md to get spec.yaml from any LLM chat (no API key)")
    p.add_argument("pdf")
    p.add_argument("-o", "--out", default="paper_prep")

    sm = sub.add_parser("simulate", help="run a generated HFSS project (HFSS Student COM mode) and analyse it")
    sm.add_argument("project", help="folder written by `run --emit-only` (contains initial/hfss_build.py)")
    sm.add_argument("--band", nargs=2, type=float, metavar=("LO", "HI"))
    sm.add_argument("--no-student", action="store_true", help="plain PyAEDT/gRPC (full HFSS licence)")
    sm.add_argument("--no-gui", action="store_true")

    an = sub.add_parser("analyse", help="S11, VSWR, Zin, gain, patterns report from an out_hfss folder")
    an.add_argument("out_hfss")
    an.add_argument("--band", nargs=2, type=float, metavar=("LO", "HI"))

    rp = sub.add_parser("replicate", help="spec.yaml -> HFSS project -> simulate -> analyse, in one command")
    rp.add_argument("--spec", required=True)
    rp.add_argument("-o", "--out", default="replica")
    rp.add_argument("--band", nargs=2, type=float, metavar=("LO", "HI"))
    rp.add_argument("--no-student", action="store_true")

    mt = sub.add_parser("match", help="from a simulated s11.csv, design two series matching sections and write a new spec")
    mt.add_argument("--s11", required=True, help="out_hfss/s11.csv of the unmatched antenna")
    mt.add_argument("--spec", required=True)
    mt.add_argument("--band", nargs=2, type=float, required=True, metavar=("LO", "HI"))
    mt.add_argument("--maxlen", type=float, default=22.0, help="max total length of the sections (mm)")
    mt.add_argument("-o", "--out", default="spec_matched.yaml")

    op = sub.add_parser("optimize", help="Bayesian optimisation of a meander spec with HFSS in the loop (resumable)")
    op.add_argument("--spec", required=True)
    op.add_argument("-o", "--out", default="opt")
    op.add_argument("--budget", type=int, default=40, help="total HFSS runs (~5-10 min each on Student)")
    op.add_argument("--init", type=int, default=8, help="random runs before the surrogate takes over")
    op.add_argument("--params", nargs="+", help="subset of N S Lcon Lr1 Wrad Wcon Lms Bw to optimise")
    op.add_argument("--mock", action="store_true", help="synthetic response, tests the loop only")
    op.add_argument("--no-student", action="store_true")
    op.add_argument("--objective", choices=["gain", "match"], default="gain", help="match = minimise worst S11 over --band")
    op.add_argument("--band", nargs=2, type=float, metavar=("LO", "HI"))
    op.add_argument("--pixels", action="store_true", help="optimise pixelated cut-outs in the copper instead of the dimensions")
    op.add_argument("--cell", type=float, default=2.0, help="pixel size in mm (--pixels)")

    r = sub.add_parser("run", help="full pipeline")
    r.add_argument("pdf", nargs="?")
    r.add_argument("-o", "--out", default="run")
    r.add_argument("-b", "--backend", choices=["mock", "hfss"], default="hfss")
    r.add_argument("--spec", help="skip extraction, use this spec.yaml")
    r.add_argument("--no-llm", action="store_true")
    r.add_argument("--emit-only", action="store_true", help="write simulator scripts, do not solve")
    r.add_argument("--no-tune", action="store_true", help="simulate once; never move parameters")
    r.add_argument("--max-iter", type=int, default=6)
    r.add_argument("--span", type=float, default=0.25, help="sweep = f0 * (1 +/- span)")
    a = ap.parse_args(argv)

    try:
        if a.cmd == "extract":
            dump_spec(extract_spec(a.pdf, use_llm=not a.no_llm), a.out)
            print(f"wrote {a.out}; review it before running")
            return 0
        if a.cmd == "simulate":
            return simulate(a.project, tuple(a.band) if a.band else None, not a.no_student, not a.no_gui)
        if a.cmd == "analyse":
            from .analyse import main as analyse_main
            analyse_main([a.out_hfss] + (["--band", str(a.band[0]), str(a.band[1])] if a.band else []))
            return 0
        if a.cmd == "replicate":
            run(None, a.out, "hfss", a.spec, False, True, 0, False, 0.25)
            return simulate(a.out, tuple(a.band) if a.band else None, not a.no_student)
        if a.cmd == "optimize":
            if a.pixels:
                from .pixels import optimise_pixels
                best = optimise_pixels(a.spec, a.out, a.budget, min(a.init, 6), a.cell, a.mock, not a.no_student)
                print("best:", json.dumps(best, indent=2))
                return 0
            from .optimize import optimise
            best = optimise(a.spec, a.out, a.budget, a.init, a.params, a.mock, not a.no_student,
                            objective=a.objective, band=tuple(a.band) if a.band else None)
            print("best:", json.dumps(best, indent=2))
            return 0
        if a.cmd == "match":
            from .match_cli import run_match
            return run_match(a.s11, a.spec, tuple(a.band), a.maxlen, a.out)
        if a.cmd == "prepare":
            d = prepare(a.pdf, a.out)
            print(f"wrote {d}/PROMPT.md, pages/*.png, spec_stub.yaml. Attach the PDF + PROMPT.md to an LLM chat, save its yaml as spec.yaml")
            return 0
        res = run(a.pdf, a.out, a.backend, a.spec, not a.no_llm, a.emit_only, a.max_iter, not a.no_tune, a.span)
        print(json.dumps(res, indent=2, default=float)[:4000])
        return 0
    except NeedsInput as ex:
        print(f"NEEDS INPUT: {ex}", file=sys.stderr)
        return 2
    except RuntimeError as ex:
        print(f"ERROR: {ex}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
