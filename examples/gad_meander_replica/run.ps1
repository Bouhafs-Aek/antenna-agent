# Paper replica (RO3003, 2.45 GHz) in HFSS Student, from the repo root:  .\examples\gad_meander_replica\run.ps1
# Uses the committed examples\gad_meander_replica\hfss\hfss_build.py (no install of the repo needed). Sign out of Windows before running.
# Needs: py -3.12 -m pip install pyaedt pywin32 ansys-pythonnet numpy matplotlib
param([int]$Tries = 4)
$root = (Get-Location).Path
$here = "examples\gad_meander_replica"
if (-not (Test-Path "$here\run.ps1")) { Write-Host "Run this from the repo root (the folder that contains 'examples')."; exit 1 }
$env:PYTHONPATH = $root
$env:ANSYSEMSV_ROOT252="C:\Program Files\ANSYS Inc\ANSYS Student\v252\AnsysEM"
$env:AEDT_VERSION="2025.2"; $env:AEDT_STUDENT="1"; $env:AEDT_GUI="1"; $env:AEDT_COM="1"
$out = "out\gad_meander_replica"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$ok = $false
for ($try = 1; $try -le $Tries -and -not $ok; $try++) {
  Get-Process ansysedt*, ansyscl* -ErrorAction SilentlyContinue | Stop-Process -Force
  Start-Sleep 5
  Remove-Item "$out\*.lock", "$out\s11.csv" -Force -ErrorAction SilentlyContinue
  Write-Host "=== replica try $try/$Tries ==="
  py -3.12 -u "$here\hfss\hfss_build.py" $out 2>&1 | Tee-Object -FilePath "$out\run_log.txt"
  $ok = Test-Path "$out\s11.csv"
}
if ($ok) {
  py -3.12 scripts\analyse.py $out --band 2.2 2.7
  Write-Host "Open $out\report\report.html"
} else {
  Write-Host "replica FAILED after $Tries tries -> $out\run_log.txt ; if HANG / 'COM table': sign out of Windows and run again."
}
