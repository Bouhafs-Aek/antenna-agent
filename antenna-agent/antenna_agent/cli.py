from __future__ import annotations

import argparse
import json
import sys

from .agent import NeedsInput, run
from .extract import extract_spec
from .spec import dump_spec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="antenna-agent", description="Antenna paper (PDF) -> HFSS/CST project")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract", help="PDF -> spec.yaml only")
    e.add_argument("pdf")
    e.add_argument("-o", "--out", default="spec.yaml")
    e.add_argument("--no-llm", action="store_true")

    r = sub.add_parser("run", help="full pipeline")
    r.add_argument("pdf", nargs="?")
    r.add_argument("-o", "--out", default="run")
    r.add_argument("-b", "--backend", choices=["mock", "hfss", "cst"], default="hfss")
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
