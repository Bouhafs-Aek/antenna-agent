"""Balayage du stub d'adaptation (Lstub, Pstub) autour de b3 FR4 s108. Usage: PYTHONPATH=. python3 scripts/make_b3_tune.py out_dir"""
import sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import make_b3_meander as m
from antenna_agent.agent import run
from antenna_agent.spec import dump_spec
ROOT = m.ROOT
out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/b3tune")
shutil.rmtree(out, ignore_errors=True)
sub = dict(name="FR4", er=4.4, tan_d=0.02, h_mm=1.6)
names = []
for kL in (0.7, 1.0, 1.4):
    for kP in (0.6, 0.8, 1.0):
        if kL == 1.0 and kP == 1.0:
            continue
        sp, s = m.spec_for("fr4", sub, 1.08)
        sp.dims_mm["Lstub"] = round(sp.dims_mm["Lstub"] * kL, 2)
        sp.dims_mm["Pstub"] = round(sp.dims_mm["Pstub"] * kP, 2)
        sp.name = f"b3_fr4_s108_L{int(kL*100)}_P{int(kP*100)}"
        f = ROOT / "examples" / f"{sp.name}.yaml"
        dump_spec(sp, f)
        run(None, str(out / sp.name / "hfss"), "hfss", str(f), emit_only=True)
        names.append(sp.name)
        print(sp.name, "Lstub", sp.dims_mm["Lstub"], "Pstub", sp.dims_mm["Pstub"])
(out / "names.txt").write_text("\n".join(names))
