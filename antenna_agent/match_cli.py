from __future__ import annotations

import numpy as np
import yaml

from .match import design2


def run_match(s11_csv: str, spec_path: str, band: tuple, maxlen: float, out: str) -> int:
    spec = yaml.safe_load(open(spec_path))
    a = np.genfromtxt(s11_csv, delimiter=",", names=True)
    n = a.dtype.names
    f, g = a[n[0]], a[n[1]] + 1j * a[n[2]]
    sub = spec["substrate"]
    r = design2(f, g, band, sub["h_mm"], sub["er"], maxlen)
    print(f"worst S11 in {band[0]}-{band[1]} GHz: {r['before_db']:.1f} dB -> predicted {r['worst_s11_db']:.1f} dB (ideal lines)")
    print(f"port side : Zt1={r['Zt1']:.1f} ohm  Wt1={r['Wt1']:.2f} mm  Lt1={r['Lt1']:.2f} mm")
    print(f"load side : Zt2={r['Zt2']:.1f} ohm  Wt2={r['Wt2']:.2f} mm  Lt2={r['Lt2']:.2f} mm")
    d = spec["dims_mm"]
    d.update(Wt1=float(round(r["Wt1"], 3)), Lt1=float(round(r["Lt1"], 2)), Wt2=float(round(r["Wt2"], 3)), Lt2=float(round(r["Lt2"], 2)))
    d["Gnd"] = float(round(max(d.get("Gnd", 0), r["Lt1"] + r["Lt2"] + 2.0), 2))
    spec["name"] = spec.get("name", "antenna") + "_matched"
    spec["notes"] = (spec.get("notes", "") + f" | matching sections predicted from simulated S11 by transmission-line "
                     f"post-processing (ideal): {r['before_db']:.1f} -> {r['worst_s11_db']:.1f} dB; verify in HFSS").strip()
    yaml.safe_dump(spec, open(out, "w"), sort_keys=False)
    print(f"wrote {out} (Gnd lengthened to {d['Gnd']} mm to carry the sections)")
    return 0
