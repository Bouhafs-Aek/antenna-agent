"""Write the LTE B3 Yagi specs (in-plane scale variants) and emit HFSS + CST projects for each."""
import json
import shutil
import sys
from pathlib import Path

import yaml

from antenna_agent.agent import run
from antenna_agent.spec import AntennaSpec, dump_spec

ROOT = Path(__file__).resolve().parent.parent
d = json.load(open(ROOT / "examples" / "b3_yagi_n7_mom.json"))
END = 25.0
SCALES = [0.96, 1.00, 1.04]


def spec_for(s: float) -> AntennaSpec:
    L, W, gap = [v * s for v in d["L"]], [v * s for v in d["W"]], [v * s for v in d["gap"]]
    n_el = len(L)                      # element e = 2 .. n_el+1
    dims = {}
    for i, (l, w) in enumerate(zip(L, W)):
        dims[f"L{i + 2}"], dims[f"W{i + 2}"] = round(l, 2), round(w, 2)
    for i, g in enumerate(gap[:n_el]):  # gap[0]=pour->driven (S12), then S23, S34, ...
        dims[f"S{i + 1}{i + 2}"] = round(g, 2)
    E = n_el + 1
    dims[f"S{E}{E + 1}"] = round(END * s, 2)
    y_end = sum(dims[f"S{e - 1}{e}"] + dims[f"W{e}"] for e in range(2, E + 1)) + dims[f"S{E}{E + 1}"]
    lp = round(d["Lp"] * s, 2)
    dims.update(Lp=lp, Bw=round(d["Bw"] * s, 2), Bl=round(lp + y_end, 2),
                Ws=0.4064, h32=0.226, h21=0.99, h10=0.226, tcu=0.0343)
    return AntennaSpec(
        name=f"b3_yagi_fr4_n7_s{int(round(s * 100)):03d}", family="printed_yagi", f0_ghz=1.795, z0_ohm=50.0,
        substrate=dict(name="FR4", er=4.4, tan_d=0.02, h_mm=1.6), dims_mm=dims, sweep_ghz=[1.6, 2.0],
        fields_ghz=[1.71, 1.795, 1.88], confidence=0.7,
        missing=["FR4 er/tan_d assumed 4.4/0.02", "balun not modelled (ideal 50 ohm port on the two-wire feed)",
                 "in-plane scale s compensates the uncertainty of the wavelength-compression factor k (calibrated 0.80+-0.02)"],
        notes=f"Designed by antenna_agent.yagi_mom (calibrated on TI DN034). In-plane scale s={s} applied to all in-plane "
              f"dims; stack-up, strip width of the two-wire feed unchanged.")


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/b3_pkg")
    shutil.rmtree(out, ignore_errors=True)
    for s in SCALES:
        sp = spec_for(s)
        f = ROOT / "examples" / f"{sp.name}.yaml"
        dump_spec(sp, f)
        for be in ("hfss", "cst"):
            run(None, str(out / f"s{int(round(s * 100)):03d}" / be), be, str(f), emit_only=True)
        print(sp.name, "board", sp.dims_mm["Bw"], "x", sp.dims_mm["Bl"], "mm")
