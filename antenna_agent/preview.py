"""Top-view geometry preview straight from the IR (what will be built), for eyeballing against the paper's figure."""
from __future__ import annotations

from pathlib import Path

from .model import Box, Cyl, Model

PALETTE = ["#9aa0a6", "#6c8ebf", "#4a7ab5", "#d9534f", "#e8a33d", "#5cb85c"]


def render(m: Model, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle

    solids = [s for s in m.solids if s.material == "pec" and not s.name.startswith(("cut_", "xt_", "xb_", "sl_", "enc_", "sma_")) and isinstance(s, (Box, Cyl))]
    levels = sorted({round(s.lo[2] if isinstance(s, Box) else s.z0, 4) for s in solids})
    col = {z: PALETTE[min(i, len(PALETTE) - 1)] for i, z in enumerate(levels)}
    zoom = [s for s in solids if s.name.startswith("a_") and isinstance(s, Box)]  # small antenna on a big board: add a zoom panel
    if zoom:
        fig, (ax, axz) = plt.subplots(1, 2, figsize=(14, 7), gridspec_kw={"width_ratios": [1, 1.6]})
    else:
        fig, ax = plt.subplots(figsize=(9, 7))
        axz = None
    for s in sorted(solids, key=lambda s: (s.lo[2] if isinstance(s, Box) else s.z0)):
        z = round(s.lo[2] if isinstance(s, Box) else s.z0, 4)
        if isinstance(s, Box):
            ax.add_patch(Rectangle((s.lo[0], s.lo[1]), s.hi[0] - s.lo[0], s.hi[1] - s.lo[1], fc=col[z], ec="k",
                                   lw=0.4, alpha=0.55))
        else:
            ax.add_patch(Circle((s.xc, s.yc), s.r, fc=col[z], ec="k", lw=0.4, alpha=0.8))
    if m.port:
        pp = (m.port.coax[0], m.port.coax[2]) if m.port.coax else m.port.p1[:2]
        ax.plot(*pp, "k*", ms=12, label=f"port {m.port.name} (y={pp[1]:.2f})")
    lo, hi = m.bbox()
    pad = 0.05 * max(hi[0] - lo[0], hi[1] - lo[1])
    ax.set_xlim(lo[0] - pad, hi[0] + pad)
    ax.set_ylim(lo[1] - pad, hi[1] + pad)
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.grid(alpha=0.25)
    ax.legend(handles=[Rectangle((0, 0), 1, 1, fc=col[z], alpha=0.6, label=f"copper @ z={z} mm") for z in levels]
              + ([ax.lines[0]] if ax.lines else []), fontsize=7, loc="lower right" if zoom else "upper right")
    ax.set_title(f"{m.name}: top view, from the IR sent to the solver (mm)")
    if axz is not None:
        for s in zoom:
            z = round(s.lo[2], 4)
            axz.add_patch(Rectangle((s.lo[0], s.lo[1]), s.hi[0] - s.lo[0], s.hi[1] - s.lo[1], fc=col[z], ec="k", lw=0.6, alpha=0.7))
        for s in m.solids:
            if isinstance(s, Cyl) and s.name == "via":
                axz.add_patch(Circle((s.xc, s.yc), s.r, fc="#d9534f", ec="k", lw=0.6))
        if m.port:
            axz.plot(*m.port.p1[:2], "k*", ms=12)
        x0, x1 = min(s.lo[0] for s in zoom), max(s.hi[0] for s in zoom)
        y0, y1 = min(s.lo[1] for s in zoom), max(s.hi[1] for s in zoom)
        axz.axhline(0, color="gray", lw=1, ls="--")
        axz.text(x0, 0.08, "ground edge (layer 2 below, y < 0)", fontsize=7, color="gray")
        axz.set_xlim(x0 - 1, x1 + 1)
        axz.set_ylim(y0 - 1.5, y1 + 1)
        axz.set_aspect("equal")
        axz.set_xlabel("x (mm)")
        axz.set_ylabel("y (mm)")
        axz.grid(alpha=0.25)
        axz.set_title("antenna zoom (top copper, star = port, red dot = via)")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
