# Driving HFSS Student 2025 R2 from PyAEDT 1.8 (Windows)

## What failed
- gRPC launch (`Failed to start on gRPC port`) fails on Student, also with `ANSYSEM_FEATURE_F335896_...`/insecure/`PYAEDT_USE_PRE_GRPC_ARGS`.
- Standalone `-Logfile` batch runs exit immediately ("No Project").

## What works: COM mode
```powershell
py -3.12 -m pip install pyaedt pywin32 ansys-pythonnet numpy matplotlib
$env:ANSYSEMSV_ROOT252="C:\Program Files\ANSYS Inc\ANSYS Student\v252\AnsysEM"
$env:AEDT_VERSION="2025.2"; $env:AEDT_STUDENT="1"; $env:AEDT_GUI="1"; $env:AEDT_COM="1"
py -3.12 hfss_build.py ..\out_hfss
```
`settings.use_grpc_api=False` makes PyAEDT start plain `ansysedtsv.exe` and attach through the Windows ROT.

## PyAEDT 1.8 API changes met
| Old | 1.8 |
|---|---|
| `hfss.AxisDir.ZPos` | `hfss.axis_directions.ZPos` |
| `SolutionData.data_real/data_imag` | `get_expression_data(expr, formula="real"/"imag")` |
| far field in one call | `insert_infinite_sphere(...)`, `get_far_field_data(..., sweeps={...})` |

`get_expression_data` returns ONE slice (other sweeps fixed at their first value). Reading a far-field array that way
gave gains of -7..-10 dBi for a 9.6 dBi antenna. Read the full array (`sd._solutions_real[expr]`, columns = sweep names + value).
**Always validate a new extraction on a paper whose answer is known.**

## Formulas used in `scripts/analyse.py`
S11_dB = 20 log10|S11|; Z = 50 (1+S11)/(1-S11); VSWR = (1+|S|)/(1-|S|) (VSWR 2 = -9.54 dB);
mismatch loss = 10 log10(1-|S11|^2); realised gain = HFSS GainTotal + mismatch loss.

## Student limits
Mesh about 128k elements; education/research licence only.
