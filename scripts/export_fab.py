"""Fabrication export of a meander design: Gerber RS-274X (top copper, bottom copper, outline), DXF, PNG preview, dimension sheet.
Usage: python scripts/export_fab.py <spec.yaml> <out_dir>
Copper = union of the PEC boxes of the geometry model (the same geometry HFSS solves). Units mm, format 4.6, one aperture-free region per box.
Gerber layers are written in board coordinates as seen from the TOP (the bottom layer is NOT mirrored): tell the fab, or check with a viewer.
No holes, no solder mask, no silk: add the SMA footprint (datasheet) and the connector pads yourself before ordering."""
import sys
from pathlib import Path

from antenna_agent.agent import make_design
from antenna_agent.model import build_model
from antenna_agent.spec import load_spec


def rects(model, h, t):
    top, bot = [], []
    for s in model.solids:
        if s.material != "pec" or not hasattr(s, "lo"):
            continue
        (x0, y0, z0), (x1, y1, z1) = s.lo, s.hi
        if abs(z0 - h) < 1e-6 and abs(z1 - (h + t)) < 1e-6:
            top.append((s.name, x0, y0, x1, y1))
        elif abs(z0 + t) < 1e-6 and abs(z1) < 1e-6:
            bot.append((s.name, x0, y0, x1, y1))
    return top, bot


def gerber(path, rs, comment):
    f = lambda v: "%d" % round(v * 1e6)
    L = ["G04 %s*" % comment, "%FSLAX46Y46*%", "%MOMM*%", "%LPD*%", "G01*"]
    for _, x0, y0, x1, y1 in rs:
        L += ["G36*", f"X{f(x0)}Y{f(y0)}D02*", "G01*", f"X{f(x1)}Y{f(y0)}D01*", f"X{f(x1)}Y{f(y1)}D01*",
              f"X{f(x0)}Y{f(y1)}D01*", f"X{f(x0)}Y{f(y0)}D01*", "G37*"]
    L.append("M02*")
    Path(path).write_text("\n".join(L) + "\n")


def outline(path, bw, bl):
    f = lambda v: "%d" % round(v * 1e6)
    xa, xb = -bw / 2, bw / 2
    L = ["G04 board outline*", "%FSLAX46Y46*%", "%MOMM*%", "%ADD10C,0.100000*%", "D10*", "G01*",
         f"X{f(xa)}Y0D02*", f"X{f(xb)}Y0D01*", f"X{f(xb)}Y{f(bl)}D01*", f"X{f(xa)}Y{f(bl)}D01*", f"X{f(xa)}Y0D01*", "M02*"]
    Path(path).write_text("\n".join(L) + "\n")


def dxf(path, layers):
    out = ["0", "SECTION", "2", "ENTITIES"]
    for lay, rs in layers.items():
        for _, x0, y0, x1, y1 in rs:
            out += ["0", "POLYLINE", "8", lay, "66", "1", "70", "1"]
            for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                out += ["0", "VERTEX", "8", lay, "10", f"{x:.4f}", "20", f"{y:.4f}", "30", "0.0"]
            out += ["0", "SEQEND", "8", lay]
    out += ["0", "ENDSEC", "0", "EOF"]
    Path(path).write_text("\n".join(out) + "\n")


def main(spec_path, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    sp = load_spec(spec_path); d = make_design(sp); m = build_model(d)
    h, t = sp.substrate.h_mm, d["t"]
    top, bot = rects(m, h, t)
    bw, bl = d["Bw"], d["Bl"]
    gerber(out / "top_copper.gtl", top, "top copper")
    gerber(out / "bottom_copper.gbl", bot, "bottom copper (as seen from the top, not mirrored)")
    outline(out / "outline.gko", bw, bl)
    dxf(out / "board.dxf", {"TOP": top, "BOTTOM": bot, "OUTLINE": [("o", -bw / 2, 0, bw / 2, bl)]})
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(1, 2, figsize=(9, 8))
    for a, rs, ttl, c in ((ax[0], top, "Top copper", "tab:orange"), (ax[1], bot, "Bottom copper (seen from top)", "tab:blue")):
        a.add_patch(Rectangle((-bw / 2, 0), bw, bl, fill=False, ec="k"))
        for _, x0, y0, x1, y1 in rs:
            a.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=c, ec="none", alpha=.85))
        a.set_xlim(-bw / 2 - 3, bw / 2 + 3); a.set_ylim(-3, bl + 3); a.set_aspect("equal"); a.set_title(ttl); a.set_xlabel("x (mm)"); a.set_ylabel("y (mm)")
    fig.tight_layout(); fig.savefig(out / "preview.png", dpi=130)
    xs = [r[1] for r in top + bot] + [r[3] for r in top + bot]
    lines = [f"Fabrication sheet - {sp.name}", "",
             f"Board outline: {bw:.2f} x {bl:.2f} mm (x from {-bw / 2:.2f} to {bw / 2:.2f}, y from 0 to {bl:.2f}); port/connector edge at y = 0",
             f"Substrate: {sp.substrate.name}, er {sp.substrate.er}, tan d {sp.substrate.tan_d}, h {h} mm; copper {t * 1000:.0f} um both sides",
             f"50 ohm strip width Wms = {d['Wms']:.3f} mm; ground plane y = 0..{d['Gnd']:.2f} mm, full board width", "",
             "Copper rectangles (name, x0, y0, x1, y1 in mm):", "TOP"]
    lines += [f"  {n}: {a:.3f} {b:.3f} {c:.3f} {e:.3f}" for n, a, b, c, e in top] + ["BOTTOM"]
    lines += [f"  {n}: {a:.3f} {b:.3f} {c:.3f} {e:.3f}" for n, a, b, c, e in bot]
    lines += ["", "Missing before ordering: SMA footprint/pads (datasheet), mask/silk, tolerances; ask the fab for the real er of its FR4."]
    (out / "fab_sheet.txt").write_text("\n".join(lines) + "\n")
    print(f"{len(top)} top + {len(bot)} bottom rectangles, board {bw:.2f} x {bl:.2f} mm -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
