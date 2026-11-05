"""Texas Instruments PCB antennas traced for KiCad from their application notes (dimension figure + table):
  an043_ifa_2g4   AN043 (SWRA117D)  small 2.4 GHz meandered IFA (CC2511 USB dongle), 15.2 x 5.7 mm, ground on layer 2
  dn023_ifa_868   DN023 (SWRA228C)  868/915/955 MHz inverted-F, FR4 0.8 mm, board 45 x 31 mm ground + antenna
  an730_mono_bom  SWRA730          BOM-tunable meander monopole (433-930 MHz + 2.4 GHz), FR4 1.6 mm, copper on both layers, antenna 43 x 25 mm
  dn024_mono_868  DN024 (SWRA227E)  868 MHz / 2440 MHz meandering monopole, FR4 1.6 mm, board 43 x 88 mm, copper on both layers
Every rectangle below is read from the note's Figure + Table; the notes say an exact copy needs TI's own Gerber/DXF (reference design zips, not provided):
overlay the Gerber of the reference design on these before ordering. mm, antenna frame: y up, ground edge at y = 0 (AN043/DN023/DN024).
Each antenna gets: <name>.kicad_pcb, <name>-F_Cu.gbr, <name>-B_Cu.gbr, <name>-Edge_Cuts.gbr, preview.png, and a lumped-port footprint P1 (pad 1 RF -> pad 2 GND).
Usage: python scripts/ti_antennas.py <out_dir>    (needs shapely, matplotlib)"""
import sys
import uuid
from pathlib import Path

from shapely.geometry import box
from shapely.ops import unary_union

OX, OY = 100.0, 100.0
R = lambda x0, x1, y0, y1: (x0, x1, y0, y1)  # rectangle: x0 x1 y0 y1


def an043():
    w = 0.5
    top = [R(0.5, 1.4, -0.5, 4.9), R(2.8, 3.3, -0.5, 4.9),                      # via leg (W1 0.9) and feed leg (W2 0.5) incl. pads D4 0.5
           R(0.5, 5.5, 4.9, 5.4),                                              # top bar L3 5.0
           R(5.0, 5.5, 2.26, 4.9), R(5.0, 8.0, 2.26, 2.76), R(7.5, 8.0, 2.26, 4.9),   # leg, bridge (L5 2.0), leg   (L4 2.64)
           R(7.5, 10.2, 4.9, 5.4),                                             # top bar L2 2.7
           R(9.7, 10.2, 2.26, 4.9), R(9.7, 12.7, 2.26, 2.76), R(12.2, 12.7, 2.26, 4.9),
           R(12.2, 14.9, 4.9, 5.4),
           R(14.4, 14.9, 1.46, 5.4)]                                           # right leg, L1 3.94
    return dict(name="an043_ifa_2g4", title="AN043 / SWRA117D - small 2.4 GHz PCB IFA", board=(0, 15.2, -20.0, 5.7), h=1.0, h_note="ASSUMED (reference-design readme not provided)",
                gr_top=top, gr_top_gnd=[], gr_bot=[R(0, 15.2, -20.0, 0)], via=[(0.95, -0.25)],
                port=[("F.Cu", "RF", 2.8, 3.3, -0.5, 0.0), ("B.Cu", "GND", 2.8, 3.3, -0.5, 0.0)], nets=False)


def dn023():
    top = [R(0, 1, 0, 20), R(6, 8, 1, 20), R(0, 13, 19, 20),                    # shorted leg, feed leg (W2 2.0, gap 1 mm to ground), top bar
           R(12, 13, 9, 20), R(12, 18, 9, 10), R(17, 18, 9, 20), R(17, 23, 19, 20),     # leg C (L4 10), bridge (L5 6 outer), leg D, top bar D-E
           R(22, 23, 9, 20), R(22, 28, 9, 10), R(27, 28, 9, 20), R(27, 33, 19, 20),
           R(32, 33, 9, 20), R(32, 38, 9, 10), R(37, 38, 9, 20), R(37, 43, 19, 20),
           R(42, 43, 3, 20),                                                    # right leg L6 17
           R(-1, 44, -31, 0)]                                                   # ground (top), X 31 x Y 45
    return dict(name="dn023_ifa_868", title="DN023 / SWRA228C - 868/915/955 MHz inverted-F", board=(-1, 44, -31, 21), h=0.8, h_note="0.8 mm FR4 (stated in the note)",
                gr_top=top, gr_top_gnd=[], gr_bot=[R(-1, 44, -31, 0)], via=[(0.5, -3.0), (0.5, -6.0)],
                port=[("F.Cu", "RF", 6, 8, 1.0, 1.5), ("F.Cu", "GND", 6, 8, -0.5, 0.0)], nets=False)


def dn024():
    ant = [R(20.5, 22.5, 1, 9), R(20.5, 40.5, 7, 9), R(38.5, 40.5, 7, 14), R(2.5, 40.5, 12, 14),      # feed leg, B4, right conn, B3
           R(2.5, 4.5, 12, 19), R(2.5, 40.5, 17, 19), R(38.5, 40.5, 17, 24), R(2.5, 40.5, 22, 24)]  # left conn, B2, right conn, B1
    gnd = [R(0, 43, -63, 0)]
    return dict(name="dn024_mono_868", title="DN024 / SWRA227E - 868 MHz / 2440 MHz meandering monopole", board=(0, 43, -63, 25), h=1.6, h_note="1.6 mm FR4 (stated in the note)",
                top_rf=ant, top_gnd=gnd, bot_rf=ant, bot_gnd=gnd, via=[(21.5, 5.0, "RF"), (21.5, 23.0, "RF")],
                port=[("F.Cu", "RF", 20.5, 22.5, 1.0, 1.5), ("F.Cu", "GND", 20.5, 22.5, -0.5, 0.0)], nets=True)


def an730():
    # serpentine (top + bottom): 4 bars W 2.0, slots L7 3.0, bars 38 long (L4); bar a is 16 long (L1); Z64 gap L2 2.0 bridged here by 0 ohm copper
    ser = [R(0, 38, 0, 2), R(0, 38, 5, 7), R(0, 38, 10, 12), R(0, 16, 15, 17), R(0, 2, 10, 17), R(36, 38, 5, 12), R(0, 2, 0, 7)]
    top_only = [R(16, 18, 15, 17), R(18, 42, 15, 17), R(18, 20, 17, 24)]            # Z64 bridge (0 ohm), bar L3 24, feed L5 7
    gnd = [R(-1, 44, 25.4, 55.4)]                                                    # L6 1.4 gap to the ground edge; ground size is a placeholder
    return dict(name="an730_mono_bom", title="SWRA730 - BOM-tunable PCB meander monopole (433-930 MHz and 2.4 GHz)", board=(-1, 44, -1, 55.4), h=1.6, h_note="1.6 mm FR4 (stated in the note)",
                top_rf=ser + top_only, top_gnd=gnd, bot_rf=ser, bot_gnd=gnd, via=[(1.0, 3.5, "RF"), (1.0, 13.5, "RF")],
                port=[("F.Cu", "RF", 18, 20, 23.5, 24.0), ("F.Cu", "GND", 18, 20, 25.4, 25.9)], nets=True)


def union(rs):
    u = unary_union([box(x0, y0, x1, y1) for x0, x1, y0, y1 in rs])
    gs = list(u.geoms) if hasattr(u, "geoms") else [u]
    return [list(g.exterior.coords)[:-1] for g in gs], u.area


def write(a, out):
    out = Path(out) / a["name"]; out.mkdir(parents=True, exist_ok=True)
    xa, xb, ya, yb = a["board"]
    kx = lambda x: OX + x - xa
    ky = lambda y: OY + yb - y
    u = lambda: str(uuid.uuid4())
    if a["nets"]:
        layers = [("F.Cu", 1, "RF", a["top_rf"]), ("F.Cu", 2, "GND", a["top_gnd"]), ("B.Cu", 1, "RF", a["bot_rf"]), ("B.Cu", 2, "GND", a["bot_gnd"])]
    else:
        layers = [("F.Cu", 0, "", a["gr_top"]), ("B.Cu", 0, "", a["gr_bot"])]
    L = ['(kicad_pcb (version 20221018) (generator "antenna-agent")', f'  (general (thickness {a["h"]}))', '  (paper "A4")',
         '  (layers (0 "F.Cu" signal) (31 "B.Cu" signal) (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen") (38 "B.Mask" user) (39 "F.Mask" user) '
         '(40 "Dwgs.User" user "User.Drawings") (41 "Cmts.User" user "User.Comments") (44 "Edge.Cuts" user) (49 "F.Fab" user))',
         '  (setup (pad_to_mask_clearance 0))', '  (net 0 "")', '  (net 1 "RF")', '  (net 2 "GND")']
    gerb = {"F.Cu": [], "B.Cu": []}
    for lay, net, nn, rs in layers:
        if not rs:
            continue
        ps, _ = union(rs); gerb[lay] += ps
        for p in ps:
            pts = " ".join(f"(xy {kx(x):.4f} {ky(y):.4f})" for x, y in p)
            if a["nets"]:
                L.append(f'  (zone (net {net}) (net_name "{nn}") (layer "{lay}") (tstamp {u()}) (hatch edge 0.5) (connect_pads (clearance 0)) (min_thickness 0.1) '
                         f'(filled_areas_thickness no) (fill yes (thermal_gap 0.5) (thermal_bridge_width 0.5)) (polygon (pts {pts})) (filled_polygon (layer "{lay}") (pts {pts})))')
            else:
                L.append(f'  (gr_poly (pts {pts}) (stroke (width 0) (type solid)) (fill solid) (layer "{lay}") (tstamp {u()}))')
    for v in a["via"]:
        net = 2 if (len(v) == 2 or v[2] == "GND") else 1
        L.append(f'  (via (at {kx(v[0]):.4f} {ky(v[1]):.4f}) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net {net}) (tstamp {u()}))')
    L.append(f'  (gr_rect (start {kx(xa):.4f} {ky(yb):.4f}) (end {kx(xb):.4f} {ky(ya):.4f}) (stroke (width 0.1) (type default)) (fill none) (layer "Edge.Cuts") (tstamp {u()}))')
    p1 = a["port"][0]; cx, cy = (p1[2] + p1[3]) / 2, (p1[4] + p1[5]) / 2
    L.append(f'  (footprint "antenna:PORT_P1" (layer "F.Cu") (tstamp {u()}) (at {kx(cx):.4f} {ky(cy):.4f}) (attr smd exclude_from_pos_files exclude_from_bom)')
    L.append(f'    (fp_text reference "P1" (at 0 -3) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))) (tstamp {u()}))')
    L.append(f'    (fp_text value "Lumped port 50 ohm: pad 1 (RF) to pad 2 (GND)" (at 0 -4.5) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.1))) (tstamp {u()}))')
    for i, (lay, nn, x0, x1, y0, y1) in enumerate(a["port"], 1):
        net = 1 if nn == "RF" else 2
        L.append(f'    (pad "{i}" smd rect (at {kx((x0 + x1) / 2) - kx(cx):.4f} {ky((y0 + y1) / 2) - ky(cy):.4f}) (size {x1 - x0:.3f} {y1 - y0:.3f}) (layers "{lay}") (net {net} "{nn}") (pinfunction "{nn}") (tstamp {u()}))')
    L[-1] += ")"
    L.append(f'  (gr_text "{a["title"]}. Board thickness {a["h"]} mm: {a["h_note"]}. Dimensions read from the note figure/table: overlay TI Gerber before ordering." (at {kx(xa):.4f} {ky(ya) + 5:.4f}) (layer "Cmts.User") (effects (font (size 1 1) (thickness 0.15)) (justify left)) (tstamp {u()}))')
    L.append(")")
    (out / f'{a["name"]}.kicad_pcb').write_text("\n".join(L) + "\n")
    f = lambda v: "%d" % round(v * 1e6)
    for lay, fn, func in (("F.Cu", "F_Cu", "Copper,L1,Top"), ("B.Cu", "B_Cu", "Copper,L2,Bot")):
        G = ["G04 antenna-agent TI antenna export*", f"%TF.FileFunction,{func}*%", "%TF.FilePolarity,Positive*%", "%FSLAX46Y46*%", "%MOMM*%", "%LPD*%", "G01*"]
        for p in gerb[lay]:
            pts = [(kx(x), -ky(y)) for x, y in p]
            G += ["G36*", f"X{f(pts[0][0])}Y{f(pts[0][1])}D02*"] + [f"X{f(x)}Y{f(y)}D01*" for x, y in pts[1:]] + [f"X{f(pts[0][0])}Y{f(pts[0][1])}D01*", "G37*"]
        G.append("M02*")
        (out / f'{a["name"]}-{fn}.gbr').write_text("\n".join(G) + "\n")
    X0, X1, Y0, Y1 = kx(xa), kx(xb), -ky(ya), -ky(yb)
    E = ["G04 board outline*", "%TF.FileFunction,Profile,NP*%", "%FSLAX46Y46*%", "%MOMM*%", "%ADD10C,0.100000*%", "D10*", "G01*",
         f"X{f(X0)}Y{f(Y0)}D02*", f"X{f(X1)}Y{f(Y0)}D01*", f"X{f(X1)}Y{f(Y1)}D01*", f"X{f(X0)}Y{f(Y1)}D01*", f"X{f(X0)}Y{f(Y0)}D01*", "M02*"]
    (out / f'{a["name"]}-Edge_Cuts.gbr').write_text("\n".join(E) + "\n")
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(1, 2, figsize=(11, 9 if a["name"] in ("dn024_mono_868", "an730_mono_bom") else 6))
    for axx, lay, t in ((ax[0], "F.Cu", "Top"), (ax[1], "B.Cu", "Bottom")):
        axx.add_patch(Rectangle((xa, ya), xb - xa, yb - ya, fill=False, ec="k"))
        for p in gerb[lay]:
            axx.fill([kx(x) - OX + xa for x, _ in p], [OY + yb - ky(y) + 0 for _, y in [(0, yy) for _, yy in p]], fc="tab:orange" if lay == "F.Cu" else "tab:blue", alpha=.8)
        axx.set_xlim(xa - 1, xb + 1); axx.set_ylim(ya - 1, yb + 1); axx.set_aspect("equal"); axx.set_title(f"{t} copper")
    fig.suptitle(a["title"]); fig.tight_layout(); fig.savefig(out / "preview.png", dpi=110)
    return {k: round(union(v)[1], 2) for k, v in (("top_mm2", a.get("gr_top") or a.get("top_rf") + a.get("top_gnd")), ("bottom_mm2", a.get("gr_bot") or a.get("bot_rf") + a.get("bot_gnd")))}


if __name__ == "__main__":
    for a in (an043(), dn023(), dn024(), an730()):
        print(a["name"], write(a, sys.argv[1]))
