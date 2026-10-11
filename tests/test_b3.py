import json, itertools
from pathlib import Path
import pytest
from antenna_agent.spec import load_spec, missing_critical
from antenna_agent.design import make_design
from antenna_agent.model import build_model, Box

EX = Path(__file__).parent.parent / "examples"
VARIANTS = ["s096", "s100", "s104"]


def _model(v):
    spec = load_spec(EX / f"b3_yagi_fr4_n7_{v}.yaml")
    return spec, build_model(make_design(spec))


@pytest.mark.parametrize("v", VARIANTS)
def test_b3_spec_complete_and_geometry(v):
    spec, m = _model(v)
    assert missing_critical(spec) == []
    dirs = [s for s in m.solids if s.name.startswith("dir")]
    assert len(dirs) == 7
    assert spec.fields_ghz == [1.71, 1.795, 1.88] and spec.sweep_ghz == [1.6, 2.0]
    # directors strictly ordered in y, no overlap
    ys = sorted((d.lo[1], d.hi[1]) for d in dirs)
    assert all(a[1] < b[0] for a, b in zip(ys, ys[1:]))
    # directors shorten monotonically-ish (never longer than driven)
    assert all(d.hi[0] - d.lo[0] < spec.dims_mm["L2"] for d in dirs)
    # everything inside the board
    slab = next(s for s in m.solids if s.name == "slab")
    for s in m.solids:
        if isinstance(s, Box) and s.name.startswith("dir"):
            assert s.lo[0] >= slab.lo[0] and s.hi[0] <= slab.hi[0] and s.hi[1] <= slab.hi[1]


@pytest.mark.parametrize("v", VARIANTS)
def test_b3_port_bridges_strips(v):
    _, m = _model(v)
    p = m.port
    ts = next(s for s in m.solids if s.name == "top_strip")
    bs = next(s for s in m.solids if s.name == "bot_strip")
    assert p.p1[2] == pytest.approx(bs.hi[2]) and p.p2[2] == pytest.approx(ts.lo[2])
    assert ts.lo[1] < p.p1[1] < ts.hi[1] and bs.lo[1] < p.p1[1] < bs.hi[1]


def test_b3_scale_variants_scale_in_plane_only():
    a, b = load_spec(EX / "b3_yagi_fr4_n7_s096.yaml"), load_spec(EX / "b3_yagi_fr4_n7_s104.yaml")
    for k in ("L2", "L9", "S23"):
        assert b.dims_mm[k] / a.dims_mm[k] == pytest.approx(1.04 / 0.96, rel=2e-3)
    for k in ("Ws", "h32", "h21", "h10", "tcu"):
        assert a.dims_mm[k] == b.dims_mm[k]


def test_b3_emitted_scripts_parse(tmp_path):
    import ast
    from antenna_agent.agent import run
    pkg = Path("/tmp/b3_pkg/s100")
    if not pkg.exists():
        pytest.skip("run scripts/make_b3_project.py first")
    ast.parse((pkg / "hfss/initial/hfss_build.py").read_text())


mom = pytest.importorskip("PyNEC")


def test_mom_dipole_directivity_2p15():
    from antenna_agent.yagi_mom import Yagi, analyze
    # free-space half-wave dipole: no pour grid, k=1 -> 2.15 dBi
    f = 1.8
    L = 0.4777 * 299.79 / f / 1.0  # mm, ~half-wave with end correction
    r = analyze(Yagi(L=[L], W=[4.0], gap=[0.0]), 1.0, f, grid=False)
    assert r["gain_dbi"] == pytest.approx(2.15, abs=0.3)


def test_mom_ti_calibration_regression():
    from antenna_agent.yagi_mom import calibrate
    rows = calibrate(ks=[0.80])
    assert rows[0]["rms"] < 0.7
