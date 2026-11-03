# Simulate the s135 variant (s=1.35) in HFSS Student, one after the other, then build the reports.
# From the repo root:  .\examples\gad_meander_b3_ro3003\run_all.ps1      (about 10-20 min per variant)
# Needs: py -3.12 -m pip install -e . pyaedt pywin32 ansys-pythonnet numpy matplotlib
$env:ANSYSEMSV_ROOT252="C:\Program Files\ANSYS Inc\ANSYS Student\v252\AnsysEM"
$env:AEDT_VERSION="2025.2"; $env:AEDT_STUDENT="1"; $env:AEDT_GUI="1"; $env:AEDT_COM="1"
$here = "examples\gad_meander_b3_ro3003"
function Stop-Aedt {   # close politely first (a hard kill leaves entries in the Windows COM table)
  $p = Get-Process ansysedt*, ansyscl* -ErrorAction SilentlyContinue
  if ($p) {
    $p | ForEach-Object { $_.CloseMainWindow() | Out-Null }
    $t = 0; while ((Get-Process ansysedt*, ansyscl* -ErrorAction SilentlyContinue) -and $t -lt 20) { Start-Sleep 2; $t += 2 }
    Get-Process ansysedt*, ansyscl* -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep 5
  }
}
Remove-Item "$here\my_results_s135.txt" -ErrorAction SilentlyContinue
foreach ($c in @(@{v="s135"; s=1.35})) {
  $out = "out_b3\$($c.v)"
  for ($try = 1; $try -le 2; $try++) {
    Stop-Aedt
    Remove-Item "$out\*.lock", "$out\s11.csv" -Force -ErrorAction SilentlyContinue
    if ($try -eq 2) { $env:ANTENNA_ATTACH = "progid" } else { Remove-Item Env:\ANTENNA_ATTACH -ErrorAction SilentlyContinue }
    Write-Host "=== $($c.v) (s=$($c.s)) try $try ==="
    py -3.12 -u "$here\$($c.v)\initial\hfss_build.py" $out 2>&1 | Tee-Object -FilePath "out_b3\run_log_$($c.v).txt"
    if (Test-Path "$out\s11.csv") { break }
  }
  if (Test-Path "$out\s11.csv") {
    py -3.12 scripts\s11_summary.py $out $c.v $c.s | Tee-Object -FilePath "$here\my_results_s135.txt" -Append
    py -3.12 scripts\analyse.py $out --band 1.71 1.88
  } else { Write-Host "$($c.v): no result, read out_b3\run_log_$($c.v).txt" }
}
Stop-Aedt
Remove-Item Env:\ANTENNA_ATTACH -ErrorAction SilentlyContinue
