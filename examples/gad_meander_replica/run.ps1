# Full pipeline for the paper replica, from the repo root:  .\examples\gad_meander_replica\run.ps1
# Needs HFSS Student 2025 R2 + `py -3.12 -m pip install -e . pyaedt pywin32 ansys-pythonnet numpy matplotlib`
$env:ANSYSEMSV_ROOT252="C:\Program Files\ANSYS Inc\ANSYS Student\v252\AnsysEM"
$env:AEDT_VERSION="2025.2"; $env:AEDT_STUDENT="1"; $env:AEDT_GUI="1"; $env:AEDT_COM="1"
$out = "out\gad_meander_replica"
py -3.12 -m antenna_agent run --spec examples\gad_meander_replica\spec.yaml -b hfss --emit-only -o $out
Get-Process ansysedt*, ansyscl* -ErrorAction SilentlyContinue | Stop-Process -Force
Push-Location "$out\initial"
py -3.12 hfss_build.py ..\out_hfss 2>&1 | Tee-Object -FilePath ..\run_log.txt
Pop-Location
py -3.12 scripts\analyse.py "$out\out_hfss" --band 2.2 2.7
Write-Host "Open $out\out_hfss\report\report.html"
