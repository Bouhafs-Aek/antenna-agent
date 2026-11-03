"""Run a generated HFSS project (initial/hfss_build.py) and analyse it: one command, HFSS Student friendly (COM mode)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

STUDENT_ROOT = r"C:\Program Files\ANSYS Inc\ANSYS Student\v252\AnsysEM"


def student_env(env: dict | None = None, gui: bool = True) -> dict:
    """Environment that makes PyAEDT drive HFSS Student 2025 R2 (gRPC does not start on Student; COM mode works)."""
    e = dict(os.environ if env is None else env)
    if "ANSYSEMSV_ROOT252" not in e and Path(STUDENT_ROOT).exists():
        e["ANSYSEMSV_ROOT252"] = STUDENT_ROOT
    e.setdefault("AEDT_VERSION", "2025.2")
    e["AEDT_STUDENT"] = "1"
    e["AEDT_COM"] = "1"
    e["AEDT_GUI"] = "1" if gui else "0"
    return e


def kill_leftovers() -> None:
    if os.name == "nt":
        for im in ("ansysedt.exe", "ansysedtsv.exe", "ansyscl.exe"):
            subprocess.run(["taskkill", "/F", "/IM", im], capture_output=True)


def simulate(project: str | Path, band: tuple[float, float] | None = None, student: bool = True, gui: bool = True) -> int:
    project = Path(project)
    script = project / "initial" / "hfss_build.py"
    if not script.exists():
        print(f"ERROR: {script} not found. Generate it first: antenna-agent run --spec SPEC.yaml -b hfss --emit-only -o {project}",
              file=sys.stderr)
        return 2
    out = project / "out_hfss"
    shutil.rmtree(out, ignore_errors=True)
    env = student_env(gui=gui) if student else dict(os.environ)
    if student:
        kill_leftovers()
    log = project / "run_log.txt"
    print(f"running {script} (HFSS {'Student, COM mode' if student else 'default mode'}); log: {log}")
    with open(log, "w", encoding="utf-8") as fh:
        p = subprocess.Popen([sys.executable, str(script), str(out)], cwd=script.parent, env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, errors="replace")
        for line in p.stdout:
            fh.write(line)
            if any(k in line for k in ("solved", "Traceback", "Error", "ERROR")):
                print(line.rstrip())
        rc = p.wait()
    if not (out / "s11.csv").exists():
        print(f"ERROR: no s11.csv produced (rc={rc}); read {log}", file=sys.stderr)
        return rc or 1
    if band is None:
        from .spec import load_spec
        sp = project / "spec.yaml"
        if sp.exists():
            s = load_spec(sp)
            if s.fields_ghz:
                band = (min(s.fields_ghz), max(s.fields_ghz))
    from .analyse import main as analyse_main
    analyse_main([str(out)] + (["--band", str(band[0]), str(band[1])] if band else []))
    print(f"Done. Open {out / 'antenna.aedt'} in HFSS (Results tree) and {out / 'report' / 'report.html'}")
    return 0
