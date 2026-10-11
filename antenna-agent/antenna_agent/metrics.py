"""S11 post-processing: resonance, depth, -10 dB bandwidth, de-embedded input impedance."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .design import C0


@dataclass
class SResult:
    f_ghz: np.ndarray
    s11: np.ndarray  # complex, at the simulator port plane


@dataclass
class Metrics:
    f_res_ghz: float
    s11_min_db: float
    bw_mhz: float
    f_z_ghz: Optional[float]  # frequency where Im(Zin)=0 nearest the S11 minimum
    z_res: Optional[complex]  # de-embedded Zin there


def deembed(res: SResult, ell_mm: float, eeff: float) -> np.ndarray:
    """Move the reference plane back along a lossless line of length ell: G_ref = G_port * exp(+j2*beta*l)."""
    beta = 2 * math.pi * res.f_ghz * 1e9 * math.sqrt(eeff) / C0
    return res.s11 * np.exp(2j * beta * ell_mm * 1e-3)


def to_z(g: np.ndarray, z0: float) -> np.ndarray:
    return z0 * (1 + g) / (1 - g)


def compute(res: SResult, z0: float, ref_shift: Optional[tuple[float, float]] = None) -> Metrics:
    f = res.f_ghz
    g_port = res.s11
    db = 20 * np.log10(np.maximum(np.abs(g_port), 1e-12))
    i0 = int(np.argmin(db))

    # -10 dB bandwidth of the contiguous region around the minimum (linear interpolation at the crossings)
    bw = 0.0
    if db[i0] <= -10:
        lo = i0
        while lo > 0 and db[lo - 1] <= -10:
            lo -= 1
        hi = i0
        while hi < len(f) - 1 and db[hi + 1] <= -10:
            hi += 1
        f_lo = f[lo] if lo == 0 else f[lo - 1] + (-10 - db[lo - 1]) / (db[lo] - db[lo - 1]) * (f[lo] - f[lo - 1])
        f_hi = f[hi] if hi == len(f) - 1 else f[hi] + (-10 - db[hi]) / (db[hi + 1] - db[hi]) * (f[hi + 1] - f[hi])
        bw = (f_hi - f_lo) * 1e3

    g_ref = deembed(res, *ref_shift) if ref_shift else g_port
    z = to_z(g_ref, z0)
    im = z.imag
    # Half-open sign test so a sample landing exactly on Im(Z)=0 is caught once (a strict product < 0 misses it).
    cands = [i for i in range(len(f) - 1)
             if ((im[i] <= 0 < im[i + 1]) or (im[i] >= 0 > im[i + 1]))
             and max(abs(im[i]), abs(im[i + 1])) < 20 * z0]
    f_z = z_res = None
    if cands:
        i = min(cands, key=lambda k: abs(f[k] - f[i0]))
        w = abs(im[i]) / (abs(im[i]) + abs(im[i + 1]))
        f_z = float(f[i] + w * (f[i + 1] - f[i]))
        z_res = complex(z[i] + w * (z[i + 1] - z[i]))
    return Metrics(float(f[i0]), float(db[i0]), float(bw), f_z, z_res)
