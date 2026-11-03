# Results (all from HFSS Student 2025 R2, files in `examples/`)

## 1. Paper replica (validation) - Gad & Sallam, Sci. Rep. 14:5769
Dimensions exactly as in the paper (`examples/gad_meander_replica/`), RO3003, 2.45 GHz.
| Quantity | Paper | This repo |
|---|---|---|
| -10 dB band | 2.2-2.7 GHz | 2.155-2.695 GHz |
| S11 min | - | -27.4 dB at 2.455 GHz |
| Zin at 2.45 GHz | - | 48 - j4 ohm |
| Gain 2.2 / 2.45 / 2.7 GHz | directivity 8.13 / 9.31 / 10.9 dBi | 8.1 / 9.6 / 10.8 dBi, end-fire +y |
Worst S11 inside 2.2-2.7 GHz: -9.1 dB at 2.70 GHz (VSWR 2.08).

## 2. LTE B3 (1.71-1.88 GHz): same geometry scaled by s = 1.368, same RO3003, no matching network
Details and files: `examples/gad_meander_b3_ro3003/`.
| Variant | s | f_res | S11 min | -10 dB band | Gain @ 1.795 |
|---|---|---|---|---|---|
| s096 | 1.313 | 1.860 GHz | -19.7 dB | 1.662-1.947 GHz | 9.3 dBi |
| **s100** | **1.368** | **1.798 GHz** | **-16.6 dB** | **1.650-1.878 GHz** | **9.4 dBi** |
| s104 | 1.422 | 1.721 GHz | -17.8 dB | 1.536-1.803 GHz | 9.6 dBi |
s100 covers B3 at S11 <= -10.1 dB over 1.71-1.88 GHz (board 75.2 x 136.8 mm). Not yet done: fabrication/measurement, radiation efficiency, connector and housing effects.

## 3. FR4 (er 4.4, tan d 0.02, h 1.6 mm)
Iteration 1 (replica on FR4, guided-wavelength scale 0.852, simulated): f_res 2.661 GHz instead of 2.45, S11 min -11.2 dB, Zin 22 - j31 ohm at 2.45 GHz, usable band 2.62-2.70 GHz only, gain 4.5 / 7.8 / 9.2 dBi at 2.2 / 2.45 / 2.7 GHz.
Corrected scale 0.925. Iteration 2 (replica and B3, three scales each) is generated and not simulated: `examples/gad_meander_fr4/`.
