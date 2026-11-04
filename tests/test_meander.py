from pathlib import Path
import pytest
from antenna_agent.spec import load_spec, missing_critical
from antenna_agent.design import make_design, eeff_ms, w50_over_h
from antenna_agent.model import build_model, Box

EX = Path(__file__).parent.parent / "examples"


def _m(name):
    sp = load_spec(EX / name)
    d = make_design(sp)
    return sp, d, build_model(d)


def test_paper_spec_complete_and_50ohm_width_matches_paper():
    sp, d, _ = _m("gad_meander_replica/spec.yaml")
    assert missing_critical(sp) == []
    assert d["Wms"] == pytest.approx(3.84, abs=0.02)  # paper text: 3.84 mm = 50 ohm on RO3003 1.527 mm
    assert d.p["Wms"].src == "derived" and d.p["Lr1"].src == "paper"
    assert d.tunable() == []


def test_rails_match_fig11_measurements():
    _, d, _ = _m("gad_meander_replica/spec.yaml")
    e = d.aux["geometry"]["e"]
    for got, meas in zip(e, [24.7, 22.2, 20.8, 19.1]):  # measured off the paper's Fig. 11, +-0.7 mm
        assert got == pytest.approx(meas, abs=0.7)


def test_geometry_inside_board_and_mirror_symmetric():
    sp, d, m = _m("gad_meander_replica/spec.yaml")
    sol = {s.name: s for s in m.solids}
    sub = sol["substrate"]
    for s in m.solids:
        if isinstance(s, Box) and s.material == "pec":
            assert s.lo[0] >= sub.lo[0] - 1e-9 and s.hi[0] <= sub.hi[0] + 1e-9
            assert s.lo[1] >= -1e-9 and s.hi[1] <= sp.dims_mm["Bl"] + 1e-9
    for n in range(1, 8):
        t, b = sol[f"t_bar{n}"], sol[f"b_bar{n}"]
        assert t.lo[0] == pytest.approx(-b.hi[0]) and t.hi[0] == pytest.approx(-b.lo[0])
        assert (t.lo[1], t.hi[1]) == (b.lo[1], b.hi[1])
    # bar pitch = Lcon
    assert sol["t_bar2"].lo[1] - sol["t_bar1"].lo[1] == pytest.approx(sp.dims_mm["Lcon"])
    # top copper above substrate, bottom below
    assert sol["ms"].lo[2] == pytest.approx(sub.hi[2]) and sol["gnd"].hi[2] == pytest.approx(sub.lo[2])


def test_port_bridges_ground_and_strip_at_board_edge():
    _, d, m = _m("gad_meander_replica/spec.yaml")
    sol = {s.name: s for s in m.solids}
    p = m.port
    assert p.p1[1] == p.p2[1] == 0.0 and p.p1[2] == pytest.approx(sol["gnd"].hi[2]) and p.p2[2] == pytest.approx(sol["ms"].lo[2])
    assert sol["gnd"].lo[1] == 0.0 and sol["ms"].lo[1] == 0.0


def test_stub_position_and_unions():
    sp, d, m = _m("gad_meander_replica/spec.yaml")
    st = next(s for s in m.solids if s.name == "stub")
    assert st.lo[1] == pytest.approx(26.5 + 4.0 - 28.5)
    assert st.hi[0] - st.lo[0] == pytest.approx(2 * 7.08 + d["Wms"])
    uni = {b.target: b.tools for b in m.booleans if b.op == "unite"}
    assert "stub" in uni["ms"] and "bstrip" in uni["gnd"]
    names = {s.name for s in m.solids}
    assert all(t in names for tools in uni.values() for t in tools)


B3 = EX / "gad_meander_b3_ro3003" / "specs"


def test_b3_scaling_rule_pure_scaling_same_substrate():
    p = load_spec(EX / "gad_meander_replica" / "spec.yaml")
    sp = load_spec(B3 / "s100.yaml")
    s = 2.455 / 1.795
    assert missing_critical(sp) == []
    assert sp.substrate.er == p.substrate.er and sp.substrate.h_mm == p.substrate.h_mm
    assert sp.dims_mm["Lr1"] == pytest.approx(p.dims_mm["Lr1"] * s, abs=0.02)
    assert sp.dims_mm["N"] == 7 and sp.dims_mm["S"] == 0.92
    assert sp.fields_ghz == [1.71, 1.795, 1.88]


def test_b3_variants_scale_all_lengths_consistently():
    a, b = load_spec(B3 / "s096.yaml"), load_spec(B3 / "s104.yaml")
    for k in ("Bl", "Bw", "Lcon", "Lr1", "Gnd", "Lms", "Wcon", "Wrad", "Lstub", "Pstub"):
        assert b.dims_mm[k] / a.dims_mm[k] == pytest.approx(1.04 / 0.96, rel=3e-3)


def test_mock_loop_runs_for_meander(tmp_path):
    from antenna_agent.agent import run
    run(None, str(tmp_path), "mock", str(EX / "gad_meander_replica/spec.yaml"))
    assert (tmp_path / "RUN.md").exists() or any(tmp_path.iterdir())


def test_fr4_cases_use_fr4_and_lambda_g_scale():
    fr4 = EX / "gad_meander_fr4"
    ro = load_spec(EX / "gad_meander_replica" / "spec.yaml")
    e = lambda er: eeff_ms(er, w50_over_h(er))
    k = 0.925  # measured on the first FR4 run (guided-wavelength guess 0.852 resonated 8.6 % high)
    for case, f_scale in (("replica", 1.0), ("b3", 2.455 / 1.795)):
        sp = load_spec(fr4 / case / "specs" / "v100.yaml")
        assert sp.substrate.er == 4.4 and sp.substrate.tan_d == 0.02 and sp.substrate.h_mm == 1.6
        assert sp.dims_mm["Lr1"] == pytest.approx(ro.dims_mm["Lr1"] * f_scale * k, abs=0.02)
        assert sp.dims_mm["N"] == 7 and sp.dims_mm["S"] == 0.92
        assert missing_critical(sp) == []


def test_fr4_b3_sma_cases_emit_a_coax_port(tmp_path):
    from antenna_agent.agent import run
    run(None, str(tmp_path), "hfss", str(EX / "gad_meander_fr4" / "b3_sma" / "specs" / "v100.yaml"), emit_only=True)
    s = (tmp_path / "initial" / "hfss_build.py").read_text()
    assert "sma_shell" in s and "wave_port" in s


def test_fr4_b3_matched_spec_has_sections_and_emits(tmp_path):
    from antenna_agent.agent import run
    sp = load_spec(EX / "gad_meander_fr4" / "b3_matched" / "specs" / "v100.yaml")
    assert sp.dims_mm["Wt1"] > 0 and sp.dims_mm["Lt1"] > 0 and sp.dims_mm["Wt2"] > 0 and sp.dims_mm["Lt2"] > 0
    run(None, str(tmp_path), "hfss", str(EX / "gad_meander_fr4" / "b3_matched" / "specs" / "v100.yaml"), emit_only=True)
    assert (tmp_path / "initial" / "hfss_build.py").exists()
