"""Adapt the Gad & Sallam antipodal meander line (2.45 GHz, RO3003) to LTE B3 and emit HFSS + CST projects.

Rule (the paper's own: "tune by the guided wavelength"): every in-plane dimension scales with lambda_g, i.e.
    s = (f_paper / f_target) * sqrt(eeff_paper / eeff_new)
with eeff the Hammerstad effective permittivity of the 50 ohm line on each substrate. Stack thickness is NOT scaled
(standard board); the 50 ohm strip width is re-derived by design.py. N and S (dimensionless) are unchanged."""
import shutil
import sys
from pathlib import Path

import yaml

from antenna_agent.agent import run
from antenna_agent.design import eeff_ms, w50_over_h
from antenna_agent.spec import dump_spec, load_spec

ROOT = Path(__file__).resolve().parent.parent
PAPER = load_spec(ROOT / "examples" / "gad_meander_2p45.yaml")
BANDS = {"b3": (1.795, [1.71, 1.795, 1.88], [1.5, 2.1]), "b40": (2.35, [2.3, 2.35, 2.4], [2.0, 2.8])}
BAND = (sys.argv[2] if len(sys.argv) > 2 else "b3").lower()
F_T, FIELDS, SWEEP = BANDS[BAND]
LENGTHS = ["Bl", "Bw", "Lcon", "Lr1", "Gnd", "Lms", "Wcon", "Wrad", "Lstub", "Pstub"]


def eeff50(er):
    return eeff_ms(er, w50_over_h(er))


def variants():
    p = PAPER.substrate
    return [("fr4", dict(name="FR4", er=4.4, tan_d=0.02, h_mm=1.6), (0.96, 1.00, 1.04, 1.08, 1.12)),
            ("ro3003", dict(name="RO3003", er=3.0, tan_d=0.001, h_mm=1.524), (1.00,))]


def spec_for(tag, sub, var):
    p = PAPER.substrate
    s_nom = (PAPER.f0_ghz / F_T) * (eeff50(p.er) / eeff50(sub["er"])) ** 0.5
    s = s_nom * var
    dims = {k: round(v * s, 2) if k in LENGTHS else v for k, v in PAPER.dims_mm.items()}
    sp = PAPER.model_copy(deep=True)
    sp.name = f"{BAND}_meander_{tag}_s{int(round(var * 100)):03d}"
    sp.f0_ghz, sp.sweep_ghz, sp.fields_ghz = F_T, SWEEP, FIELDS
    sp.substrate, sp.dims_mm, sp.reported = type(p)(**sub), dims, type(sp.reported)()
    sp.confidence = 0.6
    sp.missing = [f"scale s={s:.4f} = nominal {s_nom:.4f} x variant {var}: nominal from lambda_g scaling, NOT solver-verified",
                  "paper-implied convention for rails/stubs, see design warnings"]
    sp.notes = (f"Adapted from Gad & Sallam Sci. Rep. 14:5769 by lambda_g scaling to LTE {BAND.upper()} ({FIELDS[0]}-{FIELDS[-1]} GHz). "
                f"Paper band 2.2-2.7 GHz maps to {2.2 / PAPER.f0_ghz * F_T:.2f}-{2.7 / PAPER.f0_ghz * F_T:.2f} GHz at nominal s.")
    return sp, s


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/b3m_pkg")
    shutil.rmtree(out, ignore_errors=True)
    for be in ("hfss", "cst"):
        run(None, str(out / "paper_replica" / be), be, str(ROOT / "examples" / "gad_meander_2p45.yaml"), emit_only=True)
    for tag, sub, vs in variants():
        for var in vs:
            sp, s = spec_for(tag, sub, var)
            f = ROOT / "examples" / f"{sp.name}.yaml"
            dump_spec(sp, f)
            for be in ("hfss", "cst"):
                run(None, str(out / sp.name / be), be, str(f), emit_only=True)
            print(sp.name, f"s={s:.4f} board {sp.dims_mm['Bw']} x {sp.dims_mm['Bl']} mm")
