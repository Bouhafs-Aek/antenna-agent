"""Structured antenna specification: the contract between PDF extraction and design."""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field

Family = Literal["rect_patch", "dipole", "monopole", "printed_yagi", "meander", "ifa_meander"]

# Dimension keys (mm) the extractor may fill, per family. Anything absent is derived by design.py.
DIM_KEYS = {
    "rect_patch": {
        "W": "patch width (x, radiating-edge length)",
        "L": "patch length (y, resonant dimension, along the feed axis)",
        "Wf": "feed line width",
        "Lf": "feed line length outside the patch edge",
        "y0": "inset depth of the feed into the patch (0 = edge fed)",
        "inset_gap": "gap between feed line and patch notch on each side",
        "Wg": "ground/substrate width (x)",
        "Lg": "ground/substrate TOTAL length (y)",
        "t": "conductor thickness",
    },
    "dipole": {
        "L": "total tip-to-tip length (including feed gap)",
        "a": "wire radius",
        "gap": "feed gap",
    },
    "printed_yagi": {
        "L2": "driven dipole total length (both arms, one per copper layer)", "W2": "driven dipole width",
        "L3": "director 1 length", "L4": "director 2 length", "L5": "director 3 length",
        "W3": "director 1 width", "W4": "director 2 width", "W5": "director 3 width",
        "S12": "gap ground-pour edge -> driven element", "S23": "gap driven -> director 1",
        "S34": "gap director 1 -> 2", "S45": "gap director 2 -> 3", "S56": "gap director 3 -> board edge",
        "Bw": "board width", "Bl": "board length (total)", "Lp": "ground pour length (derived if absent)",
        "Ws": "two-wire strip width", "h32": "dielectric between the two antenna layers",
        "h21": "dielectric between antenna-bottom layer and next inner layer", "h10": "dielectric, inner to bottom layer",
        "tcu": "copper thickness", "clr": "clearance pour edge -> port plane", "via_off": "via-fence offset behind pour edge",
    },
    "meander": {
        "N": "number of dipole radiators (count, not mm)", "Bl": "board length (y, end-fire direction)",
        "Bw": "board width (x)", "Lcon": "radiator pitch (centre-to-centre, = connector length, lambda_g/8)",
        "Lr1": "first radiator length, strip centre line to inner edge of the lower connector",
        "Gnd": "truncated ground length at the feed edge", "Lms": "microstrip length to the left edge of radiator 1",
        "Wcon": "connector width (along x)", "Wrad": "radiator width (along y)", "S": "scale factor L(n)=S*L(n-1), no unit",
        "scw": "slot width in each connector (mm, 0 = none)", "scl": "connector slot length / free connector length (0..0.9)",
        "Wt1": "matching section 1 width (mm, at the port side, 0 = none)", "Lt1": "matching section 1 length",
        "Wt2": "matching section 2 width (mm, next to the radiator side)", "Lt2": "matching section 2 length",
        "srw": "slot width in each radiator (mm, 0 = none)", "srl": "radiator slot length / free radiator span (0..0.9)",
        "Lstub": "length of each of the two stubs beyond the microstrip edge", "Pstub": "stub left edge to right edge of radiator 1",
        "Wms": "50 ohm microstrip width (derived if absent)", "t": "copper thickness (derived if absent)",
    },
    "ifa_meander": {
        "L1": "open-end vertical arm length", "L2": "length of the two small top bars", "L3": "length of the first (long) top bar",
        "L4": "meander vertical length between top and bottom bars", "L5": "gap between the two verticals of a bottom bar",
        "L6": "length of the feed/short strips from the ground edge to the first top bar",
        "W1": "width of the grounded (short) strip", "W2": "trace width of everything else",
        "D1": "left board edge to the short strip", "D2": "top bars to the board top edge", "D3": "last bar to the board right edge",
        "D4": "short strip extension past the ground edge (via pad)", "D5": "gap short strip to feed strip",
        "D6": "gap feed strip to the first meander vertical",
        "Gw": "ground/substrate width (x)", "Gl": "ground/substrate length below the antenna edge (y)",
        "t": "copper thickness", "via_d": "via diameter", "feed_ext": "feed strip extension past the ground edge (port plane)",
    },
    "monopole": {
        "L": "wire height above ground plane",
        "a": "wire radius",
        "Lg": "square ground-plane side",
        "gap": "feed gap above ground",
        "t": "ground thickness",
    },
}


class Substrate(BaseModel):
    name: str = "substrate"
    er: float
    tan_d: float = 0.0
    h_mm: float


class Enclosure(BaseModel):
    """Plastic housing around the PCB: a closed shell of wall thickness t_mm, air gap gap_mm to the board sides/ends and
    gap_z_mm above/below it. Material values are typical datasheet numbers: check yours."""
    name: str = "plastic"
    er: float
    tan_d: float = 0.0
    t_mm: float = 2.5
    gap_mm: float = 5.0
    gap_z_mm: float = 5.0


class SMA(BaseModel):
    """End-launch SMA, modelled as a coax along -y that ends in a wave port: centre pin on the strip, outer shell tied to the
    bottom ground. Defaults = standard SMA (pin 1.27 mm, PTFE 4.1 mm, thread 6.35 mm): Z0 = 48.9 ohm."""
    pin_d: float = 1.27
    ptfe_d: float = 4.1
    shell_od: float = 6.35
    ptfe_er: float = 2.1
    out_mm: float = 8.0      # coax length beyond the housing wall (or beyond the board edge when there is no housing)
    free_mm: float = 10.0    # coax length when there is no housing


class Reported(BaseModel):
    """Numbers the paper claims. Used only for validation, never as design input."""
    f0_ghz: Optional[float] = None
    s11_min_db: Optional[float] = None
    bw_mhz: Optional[float] = Field(None, description="-10 dB impedance bandwidth in MHz")
    gain_dbi: Optional[float] = None


class AntennaSpec(BaseModel):
    name: str = "antenna"
    family: Family
    f0_ghz: float = Field(description="design/centre frequency in GHz")
    z0_ohm: float = 50.0
    substrate: Optional[Substrate] = None
    dims_mm: dict[str, float] = Field(
        default_factory=dict,
        description="Dimensions explicitly stated in the paper, in mm, using the key names of the family. "
        "Omit anything not stated; never guess.",
    )
    reported: Reported = Field(default_factory=Reported)
    source_pages: list[int] = Field(default_factory=list, description="1-based pages the data came from")
    confidence: float = Field(0.5, description="0..1 extractor confidence")
    missing: list[str] = Field(default_factory=list, description="Needed-but-absent items")
    notes: str = ""
    enclosure: Optional[Enclosure] = None
    sma: Optional[SMA] = None
    cell_mm: float = Field(2.0, description="pixel size for cut-out optimisation (pixels.py)")
    fields_ghz: Optional[list[float]] = Field(None, description="equally spaced GHz points where far-field is saved")
    sweep_ghz: Optional[list[float]] = Field(None, description="[fstart, fstop] GHz; default f0 +/- 25 %")
    unsupported_reason: str = Field(
        "", description="Non-empty if the radiator is NOT purely one of the supported families: parasitic elements "
        "(Yagi), arrays, slots, PIFA/IFA, horns, loops, fractals, metasurfaces, baluns/feed networks that define the "
        "match, etc. Name the structure. Leave empty only when the supported family is the whole antenna.")


def yagi_last_element(dims: dict) -> int:
    """Highest contiguous element index E with L{E} present (2 = driven, 3.. = directors); 1 = none."""
    e = 1
    while f"L{e + 1}" in dims:
        e += 1
    return e


def missing_critical(spec: AntennaSpec) -> list[str]:
    out = []
    if spec.unsupported_reason:
        out.append(f"unsupported antenna type: {spec.unsupported_reason}")
    if spec.f0_ghz <= 0:
        out.append("f0_ghz")
    if spec.family == "rect_patch" and spec.substrate is None:
        out.append("substrate (er, h_mm) is required for a patch")
    if spec.family == "printed_yagi":
        E = yagi_last_element(spec.dims_mm)
        need = ["Bw", "Bl", "Ws", "h32", "h21", "h10", "tcu"] + [f"{c}{e}" for e in range(2, E + 1) for c in "LW"] \
            + [f"S{e - 1}{e}" for e in range(2, E + 1)] + [f"S{E}{E + 1}"]
        gone = [k for k in need if k not in spec.dims_mm]
        if E < 3:
            out.append("printed_yagi needs the driven element L2/W2 and at least one director L3/W3")
        if gone:
            out.append(f"printed_yagi needs dims_mm keys (no closed-form fallback): {gone}")
        if spec.substrate is None:
            out.append("substrate (er, tan_d) required")
    if spec.family == "meander":
        need = ["N", "Bl", "Bw", "Lcon", "Lr1", "Gnd", "Lms", "Wcon", "Wrad", "S"]
        gone = [k for k in need if k not in spec.dims_mm]
        if gone:
            out.append(f"meander needs dims_mm keys (no closed-form fallback): {gone}")
        if spec.substrate is None:
            out.append("substrate (er, tan_d, h_mm) required")
        if ("Lstub" in spec.dims_mm) != ("Pstub" in spec.dims_mm):
            out.append("meander stubs need both Lstub and Pstub")
    if spec.family == "ifa_meander":
        need = ["L1", "L2", "L3", "L4", "L5", "L6", "W1", "W2", "D1", "D2", "D3", "D4", "D5", "D6"]
        gone = [k for k in need if k not in spec.dims_mm]
        if gone:
            out.append(f"ifa_meander needs dims_mm keys: {gone}")
        if spec.substrate is None:
            out.append("substrate (er, tan_d, h_mm) required (not in most antenna notes: state it as an assumption)")
    allowed = set(DIM_KEYS[spec.family])
    if spec.family == "printed_yagi":  # any number of directors: L{e}, W{e}, S{e-1}{e}, final gap S{E}{E+1}
        E = yagi_last_element(spec.dims_mm)
        allowed |= {f"{c}{e}" for e in range(2, E + 2) for c in "LW"} | {f"S{e - 1}{e}" for e in range(2, E + 2)}
    unknown = {k for k in set(spec.dims_mm) - allowed if not (spec.family == "meander" and k.startswith("cut_"))}
    if unknown:
        out.append(f"unknown dims_mm keys for {spec.family}: {sorted(unknown)}")
    return out


def load_spec(path: str | Path) -> AntennaSpec:
    return AntennaSpec(**yaml.safe_load(Path(path).read_text()))


def dump_spec(spec: AntennaSpec, path: str | Path) -> None:
    Path(path).write_text(yaml.safe_dump(spec.model_dump(mode="json"), sort_keys=False))
