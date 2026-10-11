"""Validation against the paper's claims + report.md / design.json / s11.png."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .design import Design
from .metrics import Metrics
from .tune import TuneOutcome

TOL_F = 0.02   # resonance within 2 % of the paper
TOL_BW = 0.30  # bandwidth within 30 %
MATCH = -10.0


def validate(d: Design, m: Metrics) -> list[dict]:
    r, rows = d.spec.reported, []
    if r.f0_ghz:
        err = m.f_res_ghz / r.f0_ghz - 1
        rows.append(dict(item="resonance (GHz)", paper=r.f0_ghz, sim=round(m.f_res_ghz, 4),
                         err=f"{err * 100:+.2f} %", ok=abs(err) <= TOL_F))
    rows.append(dict(item="min S11 (dB)", paper=r.s11_min_db, sim=round(m.s11_min_db, 2),
                     err="" if r.s11_min_db is None else f"{m.s11_min_db - r.s11_min_db:+.1f} dB",
                     ok=m.s11_min_db <= MATCH))
    if r.bw_mhz:
        err = m.bw_mhz / r.bw_mhz - 1
        rows.append(dict(item="-10 dB BW (MHz)", paper=r.bw_mhz, sim=round(m.bw_mhz, 1),
                         err=f"{err * 100:+.1f} %", ok=abs(err) <= TOL_BW))
    else:
        rows.append(dict(item="-10 dB BW (MHz)", paper=None, sim=round(m.bw_mhz, 1), err="", ok=None))
    if r.gain_dbi is not None:
        rows.append(dict(item="gain (dBi)", paper=r.gain_dbi, sim="not computed", err="", ok=None))
    return rows


def write_all(out: Path, d: Design, outcome: TuneOutcome, backend: str, scripts: list[Path]) -> dict:
    final = outcome.history[-1]
    rows = validate(d, final.metrics)
    summary = dict(
        backend=backend, converged=outcome.converged, note=outcome.note, iterations=len(outcome.history),
        design=d.table(), aux={k: v for k, v in d.aux.items()}, validation=rows,
        scripts=[str(p) for p in scripts],
        iterations_log=[dict(k=i.k, f_res_ghz=round(i.metrics.f_res_ghz, 4), s11_min_db=round(i.metrics.s11_min_db, 2),
                             bw_mhz=round(i.metrics.bw_mhz, 1), params={k: v["mm"] for k, v in i.params.items()})
                        for i in outcome.history])
    (out / "design.json").write_text(json.dumps(summary, indent=2, default=float))

    md = [f"# {d.spec.name} — {d.spec.family} @ {d.spec.f0_ghz} GHz  (backend: {backend})", "",
          f"**Result:** {'converged' if outcome.converged else 'NOT converged'} — {outcome.note}", ""]
    if backend == "mock":
        md += ["> **MOCK BACKEND**: analytic fixture, not an EM solve. Numbers below test the pipeline only.", ""]
    md += ["## Validation vs paper", "", "| item | paper | sim | error | pass |", "|---|---|---|---|---|"]
    for r in rows:
        ok = "—" if r["ok"] is None else ("yes" if r["ok"] else "**NO**")
        md.append(f"| {r['item']} | {r['paper'] if r['paper'] is not None else '—'} | {r['sim']} | {r['err'] or '—'} | {ok} |")
    md += ["", "## Geometry (mm) and provenance", "", "| param | value | source |", "|---|---|---|"]
    md += [f"| {k} | {v['mm']} | {v['src']} |" for k, v in d.table().items()]
    if d.aux.get("warnings"):
        md += ["", "## Warnings", ""] + [f"- {w}" for w in d.aux["warnings"]]
    if d.spec.missing:
        md += ["", "## Not found in the paper", ""] + [f"- {x}" for x in d.spec.missing]
    md += ["", "## Solver iterations", "", "| it | f_res GHz | S11 min dB | BW MHz | params |", "|---|---|---|---|---|"]
    md += [f"| {i['k']} | {i['f_res_ghz']} | {i['s11_min_db']} | {i['bw_mhz']} | {i['params']} |"
           for i in summary["iterations_log"]]
    md += ["", "## Not modelled / not validated", "",
           "- Gain, efficiency and radiation pattern are not extracted (S11 only).",
           "- Connector/SMA, substrate anisotropy, conductor roughness and finite conductivity are not modelled.",
           "- Lumped-port feed; feed-line phase is de-embedded assuming a lossless line with quasi-static eps_eff."]
    (out / "report.md").write_text("\n".join(md))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 3.6))
        for it in outcome.history:
            ax.plot(it.result.f_ghz, 20 * np.log10(np.abs(it.result.s11)), lw=1,
                    alpha=1.0 if it is outcome.history[-1] else 0.35, label=f"iter {it.k}")
        ax.axhline(-10, color="r", ls="--", lw=0.8)
        ax.axvline(d.spec.reported.f0_ghz or d.spec.f0_ghz, color="k", ls=":", lw=0.8)
        ax.set_xlabel("f (GHz)"); ax.set_ylabel("|S11| (dB)"); ax.grid(alpha=0.3); ax.legend(fontsize=7)
        fig.tight_layout(); fig.savefig(out / "s11.png", dpi=150); plt.close(fig)
    except Exception:
        pass
    return summary
