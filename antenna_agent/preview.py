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

    solids = [s for s in m.solids if s.material == "pec" and not s.name.startswith("cut_")]
    levels = sorted({round(s.lo[2] if isinstance(s, Box) else s.z0, 4) for s in solids})
    col = {z: PALETTE[min(i, len(PALETTE) - 1)] for i, z in enumerate(levels)}
    fig, ax = plt.subplots(figsize=(9, 7))
    for s in sorted(solids, key=lambda s: (s.lo[2] if isinstance(s, Box) else s.z0)):
        z = round(s.lo[2] if isinstance(s, Box) else s.z0, 4)
        if isinstance(s, Box):
            ax.add_patch(Rectangle((s.lo[0], s.lo[1]), s.hi[0] - s.lo[0], s.hi[1] - s.lo[1], fc=col[z], ec="k",
                                   lw=0.4, alpha=0.55))
        else:
            ax.add_patch(Circle((s.xc, s.yc), s.r, fc=col[z], ec="k", lw=0.4, alpha=0.8))
    if m.port:
        ax.plot(*m.port.p1[:2], "k*", ms=12, label=f"port {m.port.name} (y={m.port.p1[1]:.2f})")
    lo, hi = m.bbox()
    pad = 0.05 * max(hi[0] - lo[0], hi[1] - lo[1])
    ax.set_xlim(lo[0] - pad, hi[0] + pad)
    ax.set_ylim(lo[1] - pad, hi[1] + pad)
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.grid(alpha=0.25)
    ax.legend(handles=[Rectangle((0, 0), 1, 1, fc=col[z], alpha=0.6, label=f"copper @ z={z} mm") for z in levels]
              + ([ax.lines[0]] if ax.lines else []), fontsize=7, loc="upper right")
    ax.set_title(f"{m.name}: top view, from the IR sent to the solver (mm)")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
