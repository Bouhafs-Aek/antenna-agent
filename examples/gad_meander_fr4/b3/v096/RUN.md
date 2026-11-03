# Run (hfss)

```
PowerShell (HFSS Student, COM mode):
$env:ANSYSEMSV_ROOT252="C:\Program Files\ANSYS Inc\ANSYS Student\v252\AnsysEM"
$env:AEDT_VERSION="2025.2"; $env:AEDT_STUDENT="1"; $env:AEDT_GUI="1"; $env:AEDT_COM="1"
cd initial; py -3.12 hfss_build.py ..\out_hfss
then: py -3.12 scripts\analyse.py <this folder>\out_hfss --band LO HI
```

Sweep 1.500-2.100 GHz, 201 pts; fields saved at [1.71, 1.795, 1.88] GHz.
Outputs: s11.csv (f_GHz,re,im), gain.csv if far-field extraction worked (else gain_error.txt; read the far field in the solver GUI).

Compare `preview.png` with the paper's figure before solving.

## Modelling decisions to review
- 50 ohm microstrip width not stated: Hammerstad gives 3.059 mm for er=4.4, h=1.6
- copper thickness 35 um assumed
- meander rail depths (one lower rail per pair of radiators, scaled by S per pair) are read from the paper's Fig. 11, not stated numerically; the text states only Lr_n = S*Lr_(n-1)
- stub position convention (left edge, measured from the right edge of radiator 1) is read from Fig. 6b
- SMA connector not modelled: ideal 50 ohm lumped port at the board edge between strip and ground
