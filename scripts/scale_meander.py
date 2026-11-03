"""Same geometry, shifted frequency: scale the Gad & Sallam meander (replica spec) to another band.
Every in-plane length x s, s = f_paper / f_target (same RO3003 board, same h; the 50 ohm strip width stays derived from
the substrate; N and S unchanged). No matching network is added. Variants multiply s to straddle the target.
Usage: python scripts/scale_meander.py out_dir [f_target_GHz=1.795] [lo hi sweep GHz]"""
import sys
from pathlib import Path

from antenna_agent.agent import run
from antenna_agent.spec import dump_spec, load_spec

ROOT = Path(__file__).resolve().parent.parent
LENGTHS = ["Bl", "Bw", "Lcon", "Lr1", "Gnd", "Lms", "Wcon", "Wrad", "Lstub", "Pstub"]
F_PAPER = 2.455  # S11 minimum of our HFSS replica (2.455 GHz), the design's real resonance
VARIANTS = (0.96, 1.00, 1.04)


def main(out: str, f_t: float = 1.795, band=(1.71, 1.88), sweep=(1.5, 2.1)) -> None:
    out = Path(out)
    names = []
    for var in VARIANTS:
        sp = load_spec(ROOT / "examples" / "gad_meander_replica" / "spec.yaml")
        s = F_PAPER / f_t * var
        sp.dims_mm = {k: round(v * s, 2) if k in LENGTHS else v for k, v in sp.dims_mm.items()}
        tag = f"s{int(round(var * 100)):03d}"
        sp.name = f"gad_meander_{f_t:.3f}GHz_{tag}"
        sp.f0_ghz, sp.sweep_ghz = f_t, list(sweep)
        sp.fields_ghz = [band[0], round(f_t, 3), band[1]]
        sp.reported = type(sp.reported)()
        sp.notes = (f"Gad & Sallam meander scaled by s={s:.4f} (= {F_PAPER}/{f_t} x {var}) on the same RO3003 board; "
                    "no matching network; NOT solver-verified until simulated")
        f = out / "specs" / f"{tag}.yaml"
        f.parent.mkdir(parents=True, exist_ok=True)
        dump_spec(sp, f)
        run(None, str(out / tag), "hfss", str(f), emit_only=True)
        names.append(tag)
        print(tag, f"s={s:.4f}", "board", sp.dims_mm["Bw"], "x", sp.dims_mm["Bl"])
    cmds = [f'py -3.12 -m antenna_agent simulate "{out.name}\\{n}" --band {band[0]} {band[1]} --no-gui' for n in names]
    (out / "run_all.ps1").write_text("\n".join(cmds) + "\n")


if __name__ == "__main__":
    a = sys.argv
    main(a[1] if len(a) > 1 else "scaled", float(a[2]) if len(a) > 2 else 1.795)
