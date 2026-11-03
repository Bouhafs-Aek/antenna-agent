import ast
import json
import math

import numpy as np
import pymupdf
import pytest

from antenna_agent import emit_hfss
from antenna_agent.agent import NeedsInput, run
from antenna_agent.backends import MockBackend
from antenna_agent.design import eeff_ms, make_design, patch_rin0, w50_over_h
from antenna_agent.extract import extract_spec
from antenna_agent.metrics import SResult, compute
from antenna_agent.model import Box, build_model
from antenna_agent.spec import AntennaSpec, Substrate, dump_spec, load_spec
from antenna_agent.tune import tune

FR4 = Substrate(name="FR4", er=4.4, tan_d=0.02, h_mm=1.6)


def patch(**dims):
    return AntennaSpec(family="rect_patch", f0_ghz=2.4, substrate=FR4, dims_mm=dims)


# ---------------------------------------------------------------- physics
def test_patch_matches_balanis_textbook():
    d = make_design(patch())
    assert d["W"] == pytest.approx(38.0, abs=0.1)
    assert d["L"] == pytest.approx(29.4, abs=0.2)
    assert d.aux["dL_mm"] == pytest.approx(0.74, abs=0.02)


def test_w50_roundtrip_impedance():
    # Hammerstad analysis of the synthesised width must return ~50 ohm
    er, u = 4.4, w50_over_h(4.4)
    ee = eeff_ms(er, u)
    z = 60 / math.sqrt(ee) * math.log(8 / u + u / 4) if u <= 1 else \
        120 * math.pi / (math.sqrt(ee) * (u + 1.393 + 0.667 * math.log(u + 1.444)))
    assert z == pytest.approx(50.0, abs=1.0)


def test_rin_small_W_limit():
    # W << lambda: G1 -> W^2/(90 lambda^2)  (Balanis 14-12b)
    f0, lam = 1e9, 299_792_458 / 1e9
    W = 0.02 * lam
    _, G1, _ = patch_rin0(W, 0.3 * lam, f0)
    assert G1 == pytest.approx(W ** 2 / (90 * lam ** 2), rel=0.02)


def test_inset_hits_z0():
    d = make_design(patch())
    rin = d.aux["Rin0"] * math.cos(math.pi * d["y0"] / d["L"]) ** 2
    assert rin == pytest.approx(50.0, rel=1e-6)


def test_paper_dims_are_never_tunable():
    d = make_design(patch(L=30.0, y0=9.0))
    assert d.tunable() == [] and d.p["L"].src == "paper"
    d2 = make_design(patch(L=30.0))
    assert d2.tunable() == ["y0"]


# ---------------------------------------------------------------- metrics
def test_metrics_synthetic_resonator():
    f = np.linspace(2.0, 2.8, 801)
    z0, fr, Q, R = 50.0, 2.4, 20.0, 50.0
    z = R / (1 + 1j * Q * (f / fr - fr / f))
    m = compute(SResult(f, (z - z0) / (z + z0)), z0)
    assert m.f_res_ghz == pytest.approx(2.4, abs=0.002)
    assert m.s11_min_db < -40
    # Matched parallel RLC: |G|^2 = x^2/(4+x^2), x = Q(u - 1/u), u = f/fr. -10 dB -> x = sqrt(0.4/0.9).
    # u^2 - (x/Q)u - 1 = 0 has roots u+, u-; exact BW = (u+ - u-) fr = (x/Q) fr = 80 MHz for Q=20, fr=2.4 GHz.
    x = math.sqrt(0.4 / 0.9)
    assert m.bw_mhz == pytest.approx(x / Q * fr * 1e3, rel=1e-3)
    assert m.z_res.real == pytest.approx(R, rel=0.01)


# ---------------------------------------------------------------- geometry IR
@pytest.mark.parametrize("spec", [
    patch(),
    AntennaSpec(family="dipole", f0_ghz=2.4),
    AntennaSpec(family="monopole", f0_ghz=2.4),
])
def test_ir_is_sane(spec):
    m = build_model(make_design(spec))
    for s in m.solids:
        if isinstance(s, Box):
            assert all(h > l for l, h in zip(s.lo, s.hi)), s.name
    names = {s.name for s in m.solids}
    for b in m.booleans:
        assert b.target in names and set(b.tools) <= names
    p = m.port
    assert p.p1 != p.p2 and p.p2[2] > p.p1[2]  # integration line goes up (ZPos in the emitters)


def test_patch_port_touches_ground_and_trace():
    d = make_design(patch())
    m = build_model(d)
    assert m.port.p1[2] == 0.0 and m.port.p2[2] == pytest.approx(1.6)
    feed = next(s for s in m.solids if s.name == "feed")
    assert feed.lo[1] == pytest.approx(m.port.p1[1])  # trace starts exactly at the port plane


@pytest.mark.parametrize("fam", ["rect_patch", "dipole", "monopole"])
def test_emitted_hfss_script_is_valid_python(fam):
    spec = patch() if fam == "rect_patch" else AntennaSpec(family=fam, f0_ghz=2.4)
    m = build_model(make_design(spec))
    ast.parse(emit_hfss.emit(m))



# ---------------------------------------------------------------- closed loop (mock = plumbing test only)
@pytest.mark.parametrize("fam", ["rect_patch", "dipole", "monopole"])
def test_loop_recovers_biased_solver(tmp_path, fam):
    spec = patch() if fam == "rect_patch" else AntennaSpec(family=fam, f0_ghz=2.4)
    d = make_design(spec)
    out = tune(d, MockBackend(), tmp_path, max_iter=8)
    assert out.converged, out.note
    last = out.history[-1].metrics
    assert abs(last.f_res_ghz / 2.4 - 1) <= 0.01
    assert last.s11_min_db <= -10
    assert out.history[0].metrics.f_res_ghz != pytest.approx(last.f_res_ghz, abs=0.005)  # it actually moved


def test_loop_never_touches_paper_dims(tmp_path):
    d = make_design(patch(L=29.0, y0=10.0))  # mock resonance will be off; nothing may move
    out = tune(d, MockBackend(), tmp_path, max_iter=4)
    assert d["L"] == 29.0 and d["y0"] == 10.0
    assert len(out.history) == 1 and "stated in the paper" in out.note


# ---------------------------------------------------------------- pipeline / IO
def test_full_pipeline_mock(tmp_path):
    spec_file = tmp_path / "s.yaml"
    s = patch()
    s.reported.f0_ghz, s.reported.s11_min_db = 2.4, -25
    dump_spec(s, spec_file)
    res = run(None, str(tmp_path / "o"), "mock", str(spec_file))
    assert res["converged"]
    for f in ("report.md", "design.json", "spec.yaml", "s11.png"):
        assert (tmp_path / "o" / f).exists(), f
    assert "MOCK BACKEND" in (tmp_path / "o" / "report.md").read_text()
    assert json.loads((tmp_path / "o" / "design.json").read_text())["validation"][0]["ok"] is True
    assert list((tmp_path / "o" / "final").glob("*")) == []  # mock emits nothing


def test_emit_only_writes_solver_scripts(tmp_path):
    spec_file = tmp_path / "s.yaml"
    dump_spec(patch(), spec_file)
    run(None, str(tmp_path / "h"), "hfss", str(spec_file), emit_only=True)
    assert (tmp_path / "h/initial/hfss_build.py").exists()


def test_missing_solver_is_reported_not_faked(tmp_path, monkeypatch):
    spec_file = tmp_path / "s.yaml"
    dump_spec(patch(), spec_file)
    monkeypatch.setattr("antenna_agent.agent.available", lambda name: (False, "unavailable (test)"))
    with pytest.raises(RuntimeError, match="unavailable"):
        run(None, str(tmp_path / "o"), "hfss", str(spec_file))


def test_pdf_without_key_gives_stub_that_requires_human(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    doc = pymupdf.open()
    pg = doc.new_page()
    for i, line in enumerate(["A rectangular microstrip patch antenna at 2.4 GHz.",
                              "The substrate has dielectric constant 4.4 and thickness 1.6 mm.",
                              "Resonance at 2.4 GHz."]):
        pg.insert_text((50, 72 + 16 * i), line)  # one short line each: long lines run off the page and are clipped
    pdf = tmp_path / "p.pdf"
    doc.save(str(pdf))
    spec = extract_spec(pdf)
    assert spec.family == "rect_patch" and spec.f0_ghz == 2.4
    assert spec.substrate and spec.substrate.er == 4.4 and spec.substrate.h_mm == 1.6
    assert spec.confidence < 0.2 and spec.dims_mm == {}
    with pytest.raises(NeedsInput):
        run(str(pdf), str(tmp_path / "o"), "mock")


def test_spec_roundtrip(tmp_path):
    p = tmp_path / "s.yaml"
    dump_spec(patch(L=29.4), p)
    assert load_spec(p).dims_mm == {"L": 29.4}


def _pdf(tmp_path, lines):
    doc = pymupdf.open()
    pg = doc.new_page()
    for i, line in enumerate(lines):
        pg.insert_text((50, 72 + 16 * i), line)
    pdf = tmp_path / "x.pdf"
    doc.save(str(pdf))
    return pdf


def test_yagi_text_maps_to_printed_yagi_not_dipole_and_needs_dims(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    pdf = _pdf(tmp_path, ["2.4 GHz Yagi PCB Directional Antenna.", "The feed dipole element is fed through a balun."])
    spec = extract_spec(pdf)
    assert spec.family == "printed_yagi" and not spec.unsupported_reason
    with pytest.raises(NeedsInput, match="printed_yagi needs dims_mm"):
        run(str(pdf), str(tmp_path / "o"), "mock")


def test_slot_array_is_flagged_unsupported(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    spec = extract_spec(_pdf(tmp_path, ["A 2.4 GHz slot antenna array."]))
    assert "slot" in spec.unsupported_reason and "array" in spec.unsupported_reason


def test_unsupported_reason_blocks_even_at_high_confidence(tmp_path):
    s = patch()
    s.confidence, s.unsupported_reason = 0.95, "4-element Yagi with balun"
    p = tmp_path / "s.yaml"
    dump_spec(s, p)
    with pytest.raises(NeedsInput, match="Yagi"):
        run(None, str(tmp_path / "o"), "mock", str(p))
