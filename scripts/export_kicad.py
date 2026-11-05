"""KiCad export of a meander design: a .kicad_pcb (copper as filled polygons on F.Cu/B.Cu + Edge.Cuts) and KiCad-style Gerber X2 files
(<name>-F_Cu.gbr, <name>-B_Cu.gbr, <name>-Edge_Cuts.gbr). Copper = union of the PEC boxes of the geometry model (the one HFSS solves).
Usage: python scripts/export_kicad.py <spec.yaml> <out_dir> [name]      (needs: pip install shapely)
Board frame: connector edge (y=0) at the bottom, KiCad y axis downward, board origin offset to (100, 100) mm. Bottom copper is drawn as seen from the top (KiCad's own convention).
Add the SMA footprint in KiCad (pcbnew) on the connector edge, then File > Plot to regenerate the Gerbers if you want KiCad's own plot."""
import sys
import uuid
from pathlib import Path

from shapely.geometry import box
from shapely.ops import unary_union

from antenna_agent.agent import make_design
from antenna_agent.model import build_model
from antenna_agent.spec import load_spec
sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_fab import rects

OX, OY = 100.0, 100.0


def polys(rs):
    u = unary_union([box(x0, y0, x1, y1) for _, x0, y0, x1, y1 in rs])
    geoms = list(u.geoms) if hasattr(u, "geoms") else [u]
    for g in geoms:
        assert not list(g.interiors), "copper with holes: not handled"
    return [g.exterior.coords[:-1] for g in geoms]


def kx(x): return OX + x
def ky(y, bl): return OY + bl - y


def gerber(path, plist, bl, func, name):
    f = lambda v: "%d" % round(v * 1e6)
    L = ["G04 Created by antenna-agent export_kicad*", "%TF.GenerationSoftware,antenna-agent,export_kicad*%",
         f"%TF.FileFunction,{func}*%", "%TF.FilePolarity,Positive*%", "%FSLAX46Y46*%", "G04 Gerber Fmt 4.6, Leading zero omitted, Abs format (unit mm)*%".replace("*%", "*"),
         "%MOMM*%", "%LPD*%", "G01*"]
    for p in plist:
        pts = [(kx(x), -ky(y, bl)) for x, y in p]  # Gerber y up
        L += ["G36*", f"X{f(pts[0][0])}Y{f(pts[0][1])}D02*"] + [f"X{f(x)}Y{f(y)}D01*" for x, y in pts[1:]] + [f"X{f(pts[0][0])}Y{f(pts[0][1])}D01*", "G37*"]
    L.append("M02*")
    Path(path).write_text("\n".join(L) + "\n")


def edge(path, bw, bl):
    f = lambda v: "%d" % round(v * 1e6)
    xa, xb, ya, yb = kx(-bw / 2), kx(bw / 2), -OY - bl, -OY
    L = ["G04 Created by antenna-agent export_kicad*", "%TF.GenerationSoftware,antenna-agent,export_kicad*%", "%TF.FileFunction,Profile,NP*%",
         "%TF.FilePolarity,Positive*%", "%FSLAX46Y46*%", "%MOMM*%", "%ADD10C,0.100000*%", "D10*", "G01*",
         f"X{f(xa)}Y{f(ya)}D02*", f"X{f(xb)}Y{f(ya)}D01*", f"X{f(xb)}Y{f(yb)}D01*", f"X{f(xa)}Y{f(yb)}D01*", f"X{f(xa)}Y{f(ya)}D01*", "M02*"]
    Path(path).write_text("\n".join(L) + "\n")


def kicad_pcb(path, top, bot, bw, bl, h, wport, z0=50.0):
    """Copper as zones (top = net RF, bottom = net GND, as in the antipodal meander) + a 2-pad lumped-port footprint at the connector edge:
    pad 1 (F.Cu, net RF) on the strip end, pad 2 (B.Cu, net GND) on the ground, both at y = 0..1 mm, centred on x = 0."""
    u = lambda: str(uuid.uuid4())
    out = ['(kicad_pcb (version 20221018) (generator "antenna-agent")', f"  (general (thickness {h}))", '  (paper "A4")',
           '  (layers (0 "F.Cu" signal) (31 "B.Cu" signal) (32 "B.Adhes" user "B.Adhesive") (33 "F.Adhes" user "F.Adhesive") (34 "B.Paste" user) (35 "F.Paste" user) '
           '(36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen") (38 "B.Mask" user) (39 "F.Mask" user) (40 "Dwgs.User" user "User.Drawings") '
           '(41 "Cmts.User" user "User.Comments") (44 "Edge.Cuts" user) (45 "Margin" user) (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard") '
           '(48 "B.Fab" user) (49 "F.Fab" user))',
           f"  (setup (pad_to_mask_clearance 0) (stackup (layer \"F.Cu\" (type \"copper\") (thickness 0.035)) (layer \"dielectric 1\" (type \"core\") (thickness {h}) (material \"FR4\") (epsilon_r 4.4) (loss_tangent 0.02)) (layer \"B.Cu\" (type \"copper\") (thickness 0.035))))",
           '  (net 0 "")', '  (net 1 "RF")', '  (net 2 "GND")']
    for layer, plist, net, nn in (("F.Cu", top, 1, "RF"), ("B.Cu", bot, 2, "GND")):
        for p in plist:
            pts = " ".join(f"(xy {kx(x):.4f} {ky(y, bl):.4f})" for x, y in p)
            out.append(f'  (zone (net {net}) (net_name "{nn}") (layer "{layer}") (tstamp {u()}) (hatch edge 0.5) (connect_pads (clearance 0)) (min_thickness 0.1) '
                       f'(filled_areas_thickness no) (fill yes (thermal_gap 0.5) (thermal_bridge_width 0.5)) (polygon (pts {pts})) (filled_polygon (layer "{layer}") (pts {pts})))')
    out.append(f'  (gr_rect (start {kx(-bw / 2):.4f} {OY:.4f}) (end {kx(bw / 2):.4f} {OY + bl:.4f}) (stroke (width 0.1) (type default)) (fill none) (layer "Edge.Cuts") (tstamp {u()}))')
    y0 = ky(0.5, bl)
    out.append(f'  (footprint "antenna:PORT_P1" (layer "F.Cu") (tstamp {u()}) (at {kx(0):.4f} {y0:.4f}) (attr smd exclude_from_pos_files exclude_from_bom)')
    out.append(f'    (fp_text reference "P1" (at 0 -2.5) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))) (tstamp {u()}))')
    out.append(f'    (fp_text value "Lumped port {z0:.0f} ohm: pad 1 (RF, F.Cu) to pad 2 (GND, B.Cu), {wport:.1f} mm wide, h = {h} mm" (at 0 -4) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.1))) (tstamp {u()}))')
    out.append(f'    (pad "1" smd rect (at 0 0) (size {wport:.3f} 1) (layers "F.Cu") (net 1 "RF") (pinfunction "RF") (tstamp {u()}))')
    out.append(f'    (pad "2" smd rect (at 0 0) (size {wport:.3f} 1) (layers "B.Cu") (net 2 "GND") (pinfunction "GND") (tstamp {u()})))')
    out.append(f'  (gr_text "PORT P1 ({z0:.0f} ohm lumped, y=0 edge): RF pad (F.Cu) to GND pad (B.Cu); FR4 er 4.4 tan d 0.02 h {h} mm" (at {kx(0):.4f} {OY + bl + 4:.4f}) (layer "Cmts.User") (effects (font (size 1 1) (thickness 0.15))) (tstamp {u()}))')
    out.append(")")
    Path(path).write_text("\n".join(out) + "\n")


def main(spec_path, out, name="b3_matched"):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    sp = load_spec(spec_path); d = make_design(sp); m = build_model(d)
    h, t = sp.substrate.h_mm, d["t"]
    top, bot = rects(m, h, t)
    pt, pb = polys(top), polys(bot)
    bw, bl = d["Bw"], d["Bl"]
    wport = float(d["Wt1"]) if "Wt1" in d.p else float(d["Wms"])
    kicad_pcb(out / f"{name}.kicad_pcb", pt, pb, bw, bl, h, wport)
    gerber(out / f"{name}-F_Cu.gbr", pt, bl, "Copper,L1,Top", name)
    gerber(out / f"{name}-B_Cu.gbr", pb, bl, "Copper,L2,Bot", name)
    edge(out / f"{name}-Edge_Cuts.gbr", bw, bl)
    print(f"{len(pt)} top + {len(pb)} bottom polygons, board {bw:.2f} x {bl:.2f} mm -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
