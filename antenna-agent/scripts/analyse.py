"""Analyse les resultats HFSS d'un dossier out_hfss : S11, ROS (VSWR), impedance, gain, rayonnement.

Usage (Windows) :  py -3.12 analyse.py "<...>\\hfss\\out_hfss" [--band 1.71 1.88]
Prerequis       :  py -3.12 -m pip install numpy matplotlib
Entrees         :  s11.csv (f_GHz,re,im), gain.csv, patterns.csv (facultatif)
Sorties         :  <out_hfss>\\report\\report.html (a ouvrir dans le navigateur) + un PNG par figure
"""
from __future__ import annotations

import argparse
import base64
import csv
import io
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def read_csv(path):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]} if rows else {}


def segments(f, mask):
    """Intervalles continus [f_debut, f_fin] ou mask est vrai."""
    out, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = f[i]
        if (not m) and start is not None:
            out.append((start, f[i - 1]))
            start = None
    if start is not None:
        out.append((start, f[-1]))
    return out


def hpbw(angles_deg, g_db):
    """Largeur a -3 dB (degres) autour du maximum, sur une coupe circulaire."""
    a = np.asarray(angles_deg, float) % 360
    order = np.argsort(a)
    a, g = a[order], np.asarray(g_db, float)[order]
    n = len(a)
    i0 = int(np.argmax(g))
    thr = g[i0] - 3.0
    k = i0
    while g[(k - 1) % n] >= thr and (i0 - k) < n - 1:
        k -= 1
    j = i0
    while g[(j + 1) % n] >= thr and (j - i0) < n - 1:
        j += 1
    span = (a[j % n] - a[k % n]) % 360
    return float(span) if span > 0 else float("nan")


def fig_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_hfss")
    ap.add_argument("--band", nargs=2, type=float, metavar=("LO", "HI"), help="bande cible en GHz")
    a = ap.parse_args()
    d = Path(a.out_hfss)
    rep = d / "report"
    rep.mkdir(exist_ok=True)

    s = read_csv(d / "s11.csv")
    f = s["f_GHz"]
    S = s["re"] + 1j * s["im"]
    mag = np.abs(S)
    s11_db = 20 * np.log10(np.maximum(mag, 1e-9))
    vswr = (1 + mag) / np.maximum(1 - mag, 1e-9)
    Z = 50 * (1 + S) / (1 - S)

    g = read_csv(d / "gain.csv") if (d / "gain.csv").exists() else {}
    pat = read_csv(d / "patterns.csv") if (d / "patterns.csv").exists() else {}
    if a.band:
        lo, hi = a.band
    elif g:
        lo, hi = float(g["f_GHz"].min()), float(g["f_GHz"].max())
    else:
        lo, hi = float(f.min()), float(f.max())
    fc = 0.5 * (lo + hi)
    inb = (f >= lo) & (f <= hi)

    figs, summary = {}, []

    # ---- 1. S11
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(f, s11_db, lw=2)
    ax.axhline(-10, color="r", ls="--", lw=1, label="-10 dB")
    ax.axvspan(lo, hi, color="green", alpha=0.12, label=f"bande cible {lo:g}-{hi:g} GHz")
    im = int(np.argmin(s11_db))
    ax.plot(f[im], s11_db[im], "ko")
    ax.annotate(f"{s11_db[im]:.1f} dB @ {f[im]:.3f} GHz", (f[im], s11_db[im]), textcoords="offset points", xytext=(8, 10))
    ax.set_xlabel("Frequence (GHz)")
    ax.set_ylabel("S11 (dB)")
    ax.set_title("Coefficient de reflexion S11")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right")
    figs["s11"] = fig_png(fig)

    # ---- 2. VSWR
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(f, np.minimum(vswr, 10), lw=2, color="tab:orange")
    ax.axhline(2, color="r", ls="--", lw=1, label="ROS = 2")
    ax.axvspan(lo, hi, color="green", alpha=0.12)
    ax.set_ylim(1, 10)
    ax.set_xlabel("Frequence (GHz)")
    ax.set_ylabel("ROS (VSWR)")
    ax.set_title("Rapport d'ondes stationnaires")
    ax.grid(alpha=0.3)
    ax.legend()
    figs["vswr"] = fig_png(fig)

    # ---- 3. Impedance
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(f, Z.real, lw=2, label="Resistance R")
    ax.plot(f, Z.imag, lw=2, label="Reactance X")
    ax.axhline(50, color="tab:blue", ls=":", lw=1)
    ax.axhline(0, color="gray", ls=":", lw=1)
    ax.axvspan(lo, hi, color="green", alpha=0.12)
    ax.set_ylim(-150, 150)
    ax.set_xlabel("Frequence (GHz)")
    ax.set_ylabel("Impedance d'entree (ohm)")
    ax.set_title("Impedance d'entree (cible : R = 50, X = 0)")
    ax.grid(alpha=0.3)
    ax.legend()
    figs["z"] = fig_png(fig)

    # ---- resume S11
    segs = segments(f, s11_db < -10)
    worst_i = int(np.argmax(np.where(inb, s11_db, -1e9)))
    ic = int(np.argmin(np.abs(f - fc)))
    summary += [
        ("Minimum de S11", f"{s11_db[im]:.1f} dB a {f[im]:.3f} GHz"),
        ("Bande S11 < -10 dB", " ; ".join(f"{x:.3f}-{y:.3f} GHz" for x, y in segs) if segs else "aucune"),
        (f"Pire S11 dans {lo:g}-{hi:g} GHz", f"{s11_db[worst_i]:.1f} dB a {f[worst_i]:.3f} GHz"),
        (f"ROS max dans {lo:g}-{hi:g} GHz", f"{vswr[inb].max():.2f}" if inb.any() else "n/a"),
        (f"Impedance a {f[ic]:.3f} GHz", f"{Z[ic].real:.0f} {'+' if Z[ic].imag >= 0 else '-'} {abs(Z[ic].imag):.0f}j ohm"),
    ]

    # ---- 4. Gain
    if g:
        gf, gp = g["f_GHz"], g["peak_gain_dBi"]
        s11_at = np.interp(gf, f, mag)
        realized = gp + 10 * np.log10(np.maximum(1 - s11_at**2, 1e-9))
        fig, ax = plt.subplots(figsize=(7, 3.6))
        ax.plot(gf, gp, "o-", lw=2, label="Gain (GainTotal, sans desadaptation)")
        ax.plot(gf, realized, "s--", lw=2, label="Gain realise (avec desadaptation)")
        ax.axvspan(lo, hi, color="green", alpha=0.12)
        for x, y in zip(gf, gp):
            ax.annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0, 8), ha="center")
        ax.set_xlabel("Frequence (GHz)")
        ax.set_ylabel("Gain max (dBi)")
        ax.set_title("Gain maximal")
        ax.grid(alpha=0.3)
        ax.legend(loc="lower right")
        figs["gain"] = fig_png(fig)
        for x, y, r, th, ph in zip(gf, gp, realized, g.get("theta_deg", gf * np.nan), g.get("phi_deg", gf * np.nan)):
            summary.append((f"Gain a {x:g} GHz", f"{y:.1f} dBi (realise {r:.1f} dBi), pic a Theta {th:.0f} deg, Phi {ph:.0f} deg"))

    # ---- 5. Rayonnement
    if pat:
        fr_list = sorted(set(np.round(pat["f_GHz"], 6)))
        vmax_all = float(pat["gain_dBi"].max())
        fig, axs = plt.subplots(len(fr_list), 2, figsize=(9, 4.3 * len(fr_list)), subplot_kw={"projection": "polar"})
        axs = np.atleast_2d(axs)
        for r, fr in enumerate(fr_list):
            m = np.isclose(pat["f_GHz"], fr)
            th, ph, gd = pat["theta_deg"][m], pat["phi_deg"][m], pat["gain_dBi"][m]
            gmax = float(gd.max())

            def cut(sel_theta=None, phi_a=None, phi_b=None):
                if sel_theta is not None:
                    k = np.isclose(th, sel_theta)
                    return ph[k], gd[k]
                ka = np.isclose(ph, phi_a)
                kb = np.isclose(ph, phi_b)
                ang = np.concatenate([th[ka], -th[kb]])
                val = np.concatenate([gd[ka], gd[kb]])
                return ang, val

            # coupe YZ : angle depuis +z, positif vers +y (Phi=90) ; negatif vers -y (Phi=270)
            ang1, v1 = cut(phi_a=90.0, phi_b=270.0)
            # coupe XY : plan Theta=90, angle = Phi
            ang2, v2 = cut(sel_theta=90.0)
            for c, (ang, v, title) in enumerate([(ang1, v1, "Plan YZ (Phi=90/270 deg)\n0 deg = +z, 90 deg = +y (end-fire)"),
                                                  (ang2, v2, "Plan XY (Theta=90 deg)\nangle = Phi, 90 deg = +y")]):
                ax = axs[r, c]
                if len(ang) == 0:
                    ax.set_title("coupe indisponible")
                    continue
                o = np.argsort(ang)
                x = np.deg2rad(np.asarray(ang)[o])
                y = np.asarray(v)[o]
                ax.plot(np.append(x, x[0]), np.append(y, y[0]), lw=2)
                ax.set_theta_zero_location("N")
                ax.set_theta_direction(-1)
                ax.set_rlim(gmax - 30, gmax + 1)
                ax.set_title(f"{fr:g} GHz - {title}\npic {y.max():.1f} dBi, HPBW {hpbw(np.rad2deg(x), y):.0f} deg", fontsize=9)
                if c == 0:
                    summary.append((f"Largeur a -3 dB a {fr:g} GHz (plan YZ / plan XY)",
                                    f"{hpbw(np.rad2deg(x), y):.0f} deg / {hpbw(np.asarray(ang2) % 360, np.asarray(v2)) if len(ang2) else float('nan'):.0f} deg"))
        fig.tight_layout()
        figs["patterns"] = fig_png(fig)

        # carte Theta-Phi a la frequence centrale
        frc = fr_list[int(np.argmin(np.abs(np.array(fr_list) - fc)))]
        m = np.isclose(pat["f_GHz"], frc)
        th_u, ph_u = np.unique(pat["theta_deg"][m]), np.unique(pat["phi_deg"][m])
        grid = np.full((len(th_u), len(ph_u)), np.nan)
        for t, p, v in zip(pat["theta_deg"][m], pat["phi_deg"][m], pat["gain_dBi"][m]):
            grid[np.searchsorted(th_u, t), np.searchsorted(ph_u, p)] = v
        fig, ax = plt.subplots(figsize=(7, 3.8))
        pc = ax.pcolormesh(ph_u, th_u, grid, shading="auto", vmin=vmax_all - 30, vmax=vmax_all, cmap="turbo")
        fig.colorbar(pc, label="Gain (dBi)")
        ax.set_xlabel("Phi (deg)")
        ax.set_ylabel("Theta (deg)")
        ax.invert_yaxis()
        ax.set_title(f"Gain sur toute la sphere a {frc:g} GHz")
        figs["map"] = fig_png(fig)
    else:
        summary.append(("Rayonnement", "patterns.csv absent : relancer la simulation avec le script a jour"))

    # ---- sorties
    names = {"s11": "S11 (dB)", "vswr": "ROS (VSWR)", "z": "Impedance d'entree", "gain": "Gain",
             "patterns": "Diagrammes de rayonnement (coupes)", "map": "Gain sur toute la sphere"}
    html = ["<html><head><meta charset='utf-8'><title>Rapport antenne</title>",
            "<style>body{font-family:Segoe UI,Arial;max-width:1000px;margin:24px auto}td{padding:4px 12px;border-bottom:1px solid #ddd}"
            "img{max-width:100%}</style></head><body>",
            f"<h1>Rapport : {d.parent.parent.name}</h1><table>"]
    html += [f"<tr><td><b>{k}</b></td><td>{v}</td></tr>" for k, v in summary]
    html.append("</table>")
    for k, png in figs.items():
        (rep / f"{k}.png").write_bytes(png)
        html.append(f"<h2>{names.get(k, k)}</h2><img src='data:image/png;base64,{base64.b64encode(png).decode()}'>")
    html.append("</body></html>")
    (rep / "report.html").write_text("\n".join(html), encoding="utf-8")
    print("\n".join(f"{k:45s} {v}" for k, v in summary))
    print(f"\nRapport : {rep / 'report.html'}")


if __name__ == "__main__":
    main()
