# Simulate the LTE B3 variants (RO3003; s100 = final design) in HFSS Student and build the reports.
#   .\examples\gad_meander_b3_ro3003\run_all.ps1                 -> variants without results (none today: use -Force)
#   .\examples\gad_meander_b3_ro3003\run_all.ps1 -Force          -> all three (s100 s096 s104)
#   .\examples\gad_meander_b3_ro3003\run_all.ps1 -Only s100,s104 -> chosen variants (re-simulated)
# Run it from the repo root. Outputs: out_b3\<variant>\ (s11.csv gain.csv patterns.csv report\), summary in examples\...\my_results.txt
# Needs: py -3.12 -m pip install pyaedt pywin32 ansys-pythonnet numpy matplotlib   (the repo itself needs no install: PYTHONPATH is set here)
param([string[]]$Only, [switch]$Force, [int]$Tries = 4)
$ErrorActionPreference = "Continue"
$root = (Get-Location).Path
$here = "examples\gad_meander_b3_ro3003"
if (-not (Test-Path "$here\run_all.ps1")) { Write-Host "Run this from the repo root (the folder that contains 'examples')."; exit 1 }
$env:PYTHONPATH = $root
$env:ANSYSEMSV_ROOT252 = "C:\Program Files\ANSYS Inc\ANSYS Student\v252\AnsysEM"
$env:AEDT_VERSION = "2025.2"; $env:AEDT_STUDENT = "1"; $env:AEDT_GUI = "1"; $env:AEDT_COM = "1"
function Stop-Aedt {   # close politely first (a hard kill leaves entries in the Windows COM table)
  $p = Get-Process ansysedt*, ansyscl* -ErrorAction SilentlyContinue
  if ($p) {
    $p | ForEach-Object { $_.CloseMainWindow() | Out-Null }
    $t = 0; while ((Get-Process ansysedt*, ansyscl* -ErrorAction SilentlyContinue) -and $t -lt 20) { Start-Sleep 2; $t += 2 }
    Get-Process ansysedt*, ansyscl* -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep 5
  }
}
$all = @(@{v="s100"; s=1.3677}, @{v="s096"; s=1.3130}, @{v="s104"; s=1.4224})
$todo = @()
foreach ($c in $all) {
  if ($Only) { if ($Only -contains $c.v) { $todo += $c } }
  elseif ($Force -or -not (Test-Path "$here\$($c.v)\results\s11.csv")) { $todo += $c }
}
if (-not $todo) { Write-Host "Nothing to do: every variant already has results (use -Force to re-simulate)."; exit 0 }
Write-Host ("To simulate: " + (($todo | ForEach-Object { $_.v }) -join ", "))
New-Item -ItemType Directory -Force -Path out_b3 | Out-Null
$failed = @()
foreach ($c in $todo) {
  $out = "out_b3\$($c.v)"
  $ok = $false
  for ($try = 1; $try -le $Tries -and -not $ok; $try++) {
    Stop-Aedt
    Remove-Item "$out\*.lock", "$out\s11.csv", "$out\solver_failed.txt" -Force -ErrorAction SilentlyContinue
    Write-Host "=== $($c.v) (s=$($c.s)) try $try/$Tries ==="
    py -3.12 -u "$here\$($c.v)\initial\hfss_build.py" $out 2>&1 | Tee-Object -FilePath "out_b3\run_log_$($c.v).txt"
    $ok = Test-Path "$out\s11.csv"
    if (-not $ok -and (Test-Path "$out\solver_failed.txt")) { Write-Host "SOLVER FAILED (not a connection problem): no retry. Send $out\solver_messages.txt and $out\validation.txt"; break }
  }
  if ($ok) {
    py -3.12 scripts\s11_summary.py $out $c.v $c.s | Tee-Object -FilePath "$here\my_results.txt" -Append
    py -3.12 scripts\analyse.py $out --band 1.71 1.88
  } else {
    $failed += $c.v
    Write-Host "$($c.v): FAILED after $Tries tries -> read out_b3\run_log_$($c.v).txt ; if it says HANG or 'COM table', sign out of Windows and run again with -Only $($c.v)"
  }
}
Stop-Aedt
if ($failed) { Write-Host ("Not done: " + ($failed -join ", ")) } else { Write-Host "All requested variants done. Send out_b3\<variant>\s11.csv and gain.csv." }
