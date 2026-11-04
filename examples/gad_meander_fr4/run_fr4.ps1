# Simulate the FR4 versions of the meander in HFSS Student (FR4: er 4.4, tan d 0.02, h 1.6 mm).
#   .\examples\gad_meander_fr4\run_fr4.ps1 -Case b3_matched -> FR4 B3 with two matching sections on the feed (next step)
#   .\examples\gad_meander_fr4\run_fr4.ps1 -Case b3_final      -> matched B3, frequency-corrected (x0.9777), ideal port
#   .\examples\gad_meander_fr4\run_fr4.ps1 -Case b3_final_sma  -> same + SMA connector (the board to fabricate)
#   .\examples\gad_meander_fr4\run_fr4.ps1 -Case b3_sma    -> B3 WITH the SMA connector (after b3 / b3_matched work with the ideal port)
#   .\examples\gad_meander_fr4\run_fr4.ps1                   -> every case without results (replica, b3, b3_sma: 9 runs)
#   .\examples\gad_meander_fr4\run_fr4.ps1 -Case replica     -> only the paper replica on FR4 (2.45 GHz)
#   .\examples\gad_meander_fr4\run_fr4.ps1 -Case b3 -Only v100
# Run from the repo root. Outputs: out_fr4\<case>_<v>\ (s11.csv gain.csv patterns.csv report\), summary in examples\gad_meander_fr4\my_results.txt
# Needs: py -3.12 -m pip install pyaedt pywin32 ansys-pythonnet numpy matplotlib
param([ValidateSet("all","replica","b3","b3_sma","b3_matched","b3_final","b3_final_sma")][string]$Case = "all", [string[]]$Only, [switch]$Force, [int]$Tries = 4)
$ErrorActionPreference = "Continue"
$root = (Get-Location).Path
$here = "examples\gad_meander_fr4"
if (-not (Test-Path "$here\run_fr4.ps1")) { Write-Host "Run this from the repo root (the folder that contains 'examples')."; exit 1 }
$env:PYTHONPATH = $root
$env:ANSYSEMSV_ROOT252 = "C:\Program Files\ANSYS Inc\ANSYS Student\v252\AnsysEM"
$env:AEDT_VERSION = "2025.2"; $env:AEDT_STUDENT = "1"; $env:AEDT_GUI = "1"; $env:AEDT_COM = "1"
function Stop-Aedt {
  $p = Get-Process ansysedt*, ansyscl* -ErrorAction SilentlyContinue
  if ($p) {
    $p | ForEach-Object { $_.CloseMainWindow() | Out-Null }
    $t = 0; while ((Get-Process ansysedt*, ansyscl* -ErrorAction SilentlyContinue) -and $t -lt 20) { Start-Sleep 2; $t += 2 }
    Get-Process ansysedt*, ansyscl* -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep 5
  }
}
# case, variant, scale, target GHz, band   (b3_sma = B3 with an SMA end-launch, the version to fabricate)
$cases = @()
foreach ($v in @(@("v100",0.9250),@("v096",0.8880),@("v104",0.9620))) { $cases += ,@("replica",$v[0],$v[1],"2.45","2.2","2.7") }
foreach ($v in @(@("v100",1.2651),@("v096",1.2145),@("v104",1.3157))) { $cases += ,@("b3",$v[0],$v[1],"1.795","1.71","1.88") }
$cases += ,@("b3_matched","v100",1.2651,"1.795","1.71","1.88")
foreach ($v in @(@("v100",1.2651),@("v096",1.2145),@("v104",1.3157))) { $cases += ,@("b3_sma",$v[0],$v[1],"1.795","1.71","1.88") }
$cases += ,@("b3_final","v100",1.2369,"1.795","1.71","1.88")
$cases += ,@("b3_final_sma","v100",1.2369,"1.795","1.71","1.88")
$todo = @()
foreach ($c in $cases) {
  if ($Case -ne "all" -and $c[0] -ne $Case) { continue }
  if ($Only -and ($Only -notcontains $c[1])) { continue }
  if (-not $Force -and (Test-Path "$here\$($c[0])\$($c[1])\results\s11.csv")) { continue }
  $todo += ,$c
}
if (-not $todo) { Write-Host "Nothing to do (use -Force to re-simulate)."; exit 0 }
New-Item -ItemType Directory -Force -Path out_fr4 | Out-Null
$failed = @()
foreach ($c in $todo) {
  $name = "$($c[0])_$($c[1])"; $out = "out_fr4\$name"; $ok = $false
  for ($try = 1; $try -le $Tries -and -not $ok; $try++) {
    Stop-Aedt
    Remove-Item "$out\*.lock", "$out\s11.csv", "$out\solver_failed.txt" -Force -ErrorAction SilentlyContinue
    Write-Host "=== $name (s=$($c[2])) try $try/$Tries ==="
    py -3.12 -u "$here\$($c[0])\$($c[1])\initial\hfss_build.py" $out 2>&1 | Tee-Object -FilePath "out_fr4\run_log_$name.txt"
    $ok = Test-Path "$out\s11.csv"
    if (-not $ok -and (Test-Path "$out\solver_failed.txt")) { Write-Host "HFSS solver failed on this try (intermittent: b3_matched failed once, then solved). Messages kept in $out\solver_messages_try$try.txt; retrying."; Copy-Item "$out\solver_messages.txt" "$out\solver_messages_try$try.txt" -Force -ErrorAction SilentlyContinue }
  }
  if ($ok) {
    py -3.12 scripts\s11_summary.py $out $name $c[2] $c[3] | Tee-Object -FilePath "$here\my_results.txt" -Append
    py -3.12 scripts\analyse.py $out --band $c[4] $c[5]
  } else {
    $failed += $name
    Write-Host "$name FAILED after $Tries tries -> read out_fr4\run_log_$name.txt ; if HANG / 'COM table': sign out of Windows, then -Case $($c[0]) -Only $($c[1])"
  }
}
Stop-Aedt
if ($failed) { Write-Host ("Not done: " + ($failed -join ", ")) } else { Write-Host "Done. Send the s11.csv and gain.csv of each out_fr4\<case>_<v> folder." }
