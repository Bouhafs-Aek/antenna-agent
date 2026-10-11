"""Solver backends. hfss / cst emit scripts and run them in a subprocess; mock is an analytic test fixture."""
from __future__ import annotations

import csv
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from . import emit_cst, emit_hfss
from .design import C0
from .metrics import SResult
from .model import Model


def read_s11_csv(path: Path) -> SResult:
    rows = list(csv.reader(path.open()))[1:]
    a = np.array([[float(x) for x in r] for r in rows])
    return SResult(a[:, 0], a[:, 1] + 1j * a[:, 2])


class Backend:
    name = "base"

    def emit(self, m: Model, d: Path) -> list[Path]:
        raise NotImplementedError

    def run(self, m: Model, d: Path) -> SResult:
        raise NotImplementedError


class HfssBackend(Backend):
    name = "hfss"

    def emit(self, m, d):
        d.mkdir(parents=True, exist_ok=True)
        p = d / "hfss_build.py"
        p.write_text(emit_hfss.emit(m))
        return [p]

    def run(self, m, d):
        (script,) = self.emit(m, d)
        py = os.environ.get("AEDT_PYTHON", sys.executable)
        r = subprocess.run([py, str(script), str(d)], capture_output=True, text=True)
        (d / "run.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr)
        if r.returncode != 0 or not (d / "s11.csv").exists():
            raise RuntimeError(f"HFSS run failed (rc={r.returncode}); see {d / 'run.log'}\n{r.stderr[-1500:]}")
        return read_s11_csv(d / "s11.csv")


class CstBackend(Backend):
    name = "cst"

    def emit(self, m, d):
        d.mkdir(parents=True, exist_ok=True)
        a, b = d / "cst_build.py", d / "cst_build.bas"
        a.write_text(emit_cst.emit_driver(m))
        b.write_text(emit_cst.emit_bas(m))
        return [a, b]

    def run(self, m, d):
        script = self.emit(m, d)[0]
        py = os.environ.get("CST_PYTHON", sys.executable)
        r = subprocess.run([py, str(script), str(d)], capture_output=True, text=True)
        (d / "run.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr)
        if r.returncode != 0 or not (d / "s11.csv").exists():
            raise RuntimeError(f"CST run failed (rc={r.returncode}); see {d / 'run.log'}\n{r.stderr[-1500:]}")
        return read_s11_csv(d / "s11.csv")


class MockBackend(Backend):
    """Lumped-resonator stand-in with deliberate bias (resonance -3.5 %, resistance +15 %), so the tuning loop has
    something real to correct. A TEST FIXTURE for the plumbing. It is not an EM solver and proves nothing about
    antennas."""
    name = "mock"
    F_BIAS, R_BIAS = 0.965, 1.15

    def emit(self, m, d):
        d.mkdir(parents=True, exist_ok=True)
        return []

    def run(self, m, d):
        dsg = m.design
        f = np.linspace(m.fmin, m.fmax, m.npts)
        z0 = dsg.spec.z0_ohm
        fam = dsg.spec.family
        if fam == "rect_patch":
            L, y0 = dsg["L"], dsg["y0"]
            fr = C0 / (2 * (L + 2 * dsg.aux["dL_mm"]) * 1e-3 * math.sqrt(dsg.aux["eeff"])) / 1e9 * self.F_BIAS
            R = dsg.aux["Rin0"] * math.cos(math.pi * y0 / L) ** 2 * self.R_BIAS
            z = R / (1 + 1j * 22 * (f / fr - fr / f))
            g = (z - z0) / (z + z0)
            ell, eeff_l = m.ref_shift
            beta = 2 * math.pi * f * 1e9 * math.sqrt(eeff_l) / C0
            g = g * np.exp(-2j * beta * ell * 1e-3)
        else:
            k = 0.46 if fam in ("dipole", "meander") else 0.23
            R = 73.0 if fam in ("dipole", "meander") else 36.5
            fr = k * C0 / ((dsg["L"] if "L" in dsg.p else dsg.aux["L_eq"]) * 1e-3) / 1e9
            z = R + 1j * 8 * R * (f / fr - fr / f)
            g = (z - z0) / (z + z0)
        return SResult(f, g)


def get_backend(name: str) -> Backend:
    return {"hfss": HfssBackend, "cst": CstBackend, "mock": MockBackend}[name]()


def available(name: str) -> tuple[bool, str]:
    """Best-effort check that the solver's python bindings can be imported by the interpreter we will use."""
    if name == "mock":
        return True, "analytic fixture"
    py = os.environ.get("AEDT_PYTHON" if name == "hfss" else "CST_PYTHON", sys.executable)
    mod = "ansys.aedt.core" if name == "hfss" else "cst.interface"
    r = subprocess.run([py, "-c", f"import {mod}"], capture_output=True, text=True)
    if r.returncode == 0:
        return True, py
    if name == "hfss":  # older releases
        r = subprocess.run([py, "-c", "import pyaedt"], capture_output=True, text=True)
        if r.returncode == 0:
            return True, py
    hint = "set AEDT_PYTHON to an interpreter with ansys-aedt-core" if name == "hfss" \
        else "set CST_PYTHON to an interpreter with the cst package (CST install: Library/Python)"
    return False, f"cannot import {mod} with {py}; {hint}"
