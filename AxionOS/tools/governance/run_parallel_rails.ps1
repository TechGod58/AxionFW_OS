#requires -Version 5.1
<#
run_parallel_rails.ps1
- Timeout-safe orchestrator for file-based rail execution.
- Emits heartbeat every 45s to stdout + log.
- Supports phased execution (B1..B5), resume, and strict preflight gates.
- Avoids here-strings and large inline payloads.
#>
[CmdletBinding()]
param(
  [switch]$SelfTest,
  [string]$PlanPath = "",
  [ValidateSet("A","B","C","ALL")]
  [string]$Rails = "ALL",
  [ValidateSet("B1","B2","B3","B4","B5","")]
  [string]$ResumeFromPhase = "",
  [int]$HeartbeatSec = 45
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot '..\common\pathing.ps1')
$osRoot = Get-AxionOsRoot -ScriptPath $PSCommandPath
Enable-AxionLocalRuntimePath -OsRoot $osRoot
$script:pythonInvocation = Get-AxionPythonInvocation -OsRoot $osRoot
if([string]::IsNullOrWhiteSpace($PlanPath)){
  $PlanPath = Join-Path $osRoot 'out\governance\rails\rail_plan.json'
}

# ----------------------------
# Paths
# ----------------------------
$RailsDir = Join-Path $osRoot "out\governance\rails"
$LogsDir = Join-Path $RailsDir "logs"
New-Item -ItemType Directory -Force $RailsDir | Out-Null
New-Item -ItemType Directory -Force $LogsDir | Out-Null

$SelfTestLog = Join-Path $RailsDir "run_parallel_rails_selftest.log"
$RunLog = Join-Path $RailsDir ("run_parallel_rails_{0}.log" -f (Get-Date -Format "yyyyMMddTHHmmssZ"))

# ----------------------------
# Heartbeat (job-based; stop-file)
# ----------------------------
$script:hbJob = $null
$script:hbStopFile = $null

function Start-Heartbeat {
  param(
    [Parameter(Mandatory=$true)][string]$Phase,
    [Parameter(Mandatory=$true)][string]$LogPath,
    [int]$IntervalSec = 45
  )

  # Stop any prior heartbeat
  Stop-Heartbeat -LogPath $LogPath -Silent

  $script:hbStopFile = Join-Path $env:TEMP ("axion_hb_stop_{0}.flag" -f ([guid]::NewGuid().ToString("N")))
  $start = Get-Date

  $script:hbJob = Start-Job -ArgumentList $Phase,$LogPath,$IntervalSec,$start,$script:hbStopFile -ScriptBlock {
    param($phase,$logPath,$intervalSec,$startTime,$stopFile)

    while (-not (Test-Path $stopFile)) {
      $elapsed = [int]((Get-Date) - $startTime).TotalSeconds
      $line = "[rail] HEARTBEAT phase=$phase step=?/? elapsed_s=$elapsed"
      try {
        $line | Out-Host
        Add-Content -Path $logPath -Value $line
      } catch {
        # swallow heartbeat write errors; do not kill rail execution
      }
      Start-Sleep -Seconds $intervalSec
    }
  }
}

function Stop-Heartbeat {
  param(
    [Parameter(Mandatory=$true)][string]$LogPath,
    [switch]$Silent
  )

  try {
    if ($script:hbStopFile) {
      New-Item -ItemType File -Force -Path $script:hbStopFile | Out-Null
    }
    if ($script:hbJob) {
      Wait-Job $script:hbJob -Timeout 10 | Out-Null
      Remove-Job $script:hbJob -Force -ErrorAction SilentlyContinue
    }
  } catch {
    if (-not $Silent) { throw }
  } finally {
    $script:hbJob = $null
    $script:hbStopFile = $null
  }
}

# ----------------------------
# Logging helpers
# ----------------------------
function Log-Line {
  param([Parameter(Mandatory=$true)][string]$Line, [Parameter(Mandatory=$true)][string]$LogPath)
  $Line | Out-Host
  Add-Content -Path $LogPath -Value $Line
}

function Write-PhaseMarker {
  param(
    [Parameter(Mandatory=$true)][string]$PhaseId,
    [Parameter(Mandatory=$true)][string]$Kind, # start|done
    [Parameter(Mandatory=$true)][string]$Dir,
    [string]$Extra = ""
  )
  $p = Join-Path $Dir ("phase_{0}_{1}.txt" -f $PhaseId,$Kind)
  $ts = (Get-Date).ToUniversalTime().ToString("o")
  Set-Content -Path $p -Value ("{0} {1} {2}" -f $ts,$PhaseId,$Extra)
}

# ----------------------------
# Safe command runner
# ----------------------------
function Run-Cmd {
param(
  [Parameter(Mandatory=$true)][string]$Name,
  [Parameter(Mandatory=$true)][string]$FilePath,
  [Parameter()][string[]]$Args = @(),
  [Parameter(Mandatory=$true)][string]$LogPath
)

Log-Line ("[rail] CMD_START name={0} file={1} args={2}" -f $Name,$FilePath,($Args -join " ")) $LogPath
try {
  $null = & $FilePath @Args
  $exitCode = $LASTEXITCODE
  if($null -eq $exitCode){ $exitCode = 0 }
} catch {
  $exitCode = 1
  Log-Line ("[rail] CMD_ERR name={0} error={1}" -f $Name,$_.Exception.Message) $LogPath
}
Log-Line ("[rail] CMD_DONE name={0} exit={1}" -f $Name,$exitCode) $LogPath
return $exitCode
}

# ----------------------------
# Preflight gates (must be green)
# ----------------------------
function Run-Preflight {
  param([Parameter(Mandatory=$true)][string]$LogPath)

  Log-Line "[rail] PREFLIGHT_START" $LogPath
  Start-Heartbeat -Phase "preflight" -LogPath $LogPath -IntervalSec $HeartbeatSec
  try {
    $reg = Run-Cmd -Name "validate_registry" -FilePath $script:pythonInvocation.file_path -Args @($script:pythonInvocation.args_prefix + (Join-Path $osRoot "tools\contracts\validate_registry.py")) -LogPath $LogPath
    if ($reg -ne 0) { throw "Preflight failed: REG_EXIT=$reg" }

    $self = Run-Cmd -Name "gate_selfcheck" -FilePath "powershell" -Args @("-NoProfile","-ExecutionPolicy","Bypass","-File",(Join-Path $osRoot "ci\pipeline_contracts_gate.ps1"),"-SelfCheck") -LogPath $LogPath
    if ($self -ne 0) { throw "Preflight failed: SELF_CHECK_EXIT=$self" }

    $drift = Run-Cmd -Name "drift_check" -FilePath $script:pythonInvocation.file_path -Args @($script:pythonInvocation.args_prefix + (Join-Path $osRoot "tools\governance\emit_governance_drift_check.py")) -LogPath $LogPath
    if ($drift -ne 0) { throw "Preflight failed: DRIFT_CHECK_EXIT=$drift" }

    Log-Line "[rail] PREFLIGHT_DONE REG_EXIT=0 SELF_CHECK_EXIT=0 DRIFT_CHECK_EXIT=0" $LogPath
  }
  finally {
    Stop-Heartbeat -LogPath $LogPath -Silent
  }
}

# ----------------------------
# Load plan (optional)
# Expected JSON shape (minimal):
# {
#   "railA": { "script": "<osRoot>\tools\governance\rails\run_rail_A.ps1" },
#   "railB": { "phases": ["B1","B2","B3","B4","B5"], "workersDir": "<osRoot>\tools\governance\workers" },
#   "railC": { "script": "<osRoot>\tools\governance\rails\run_rail_C.ps1" }
# }
# If absent, we fall back to defaults.
# ----------------------------
function Load-Plan {
  param([string]$Path)
  if (Test-Path $Path) {
    return Get-Content $Path -Raw | ConvertFrom-Json
  }
  return $null
}

function Resolve-PlanPathValue {
  param(
    [string]$PathValue,
    [Parameter(Mandatory=$true)][string]$BaseRoot
  )
  if ([string]::IsNullOrWhiteSpace($PathValue)) {
    return $PathValue
  }
  $value = [string]$PathValue
  $legacyPrefix = "C:\AxionOS"
  if ($value.StartsWith($legacyPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    $suffix = $value.Substring($legacyPrefix.Length).TrimStart('\','/')
    if ([string]::IsNullOrWhiteSpace($suffix)) { return $BaseRoot }
    return Join-Path $BaseRoot ($suffix -replace '/', '\')
  }
  if ([System.IO.Path]::IsPathRooted($value)) {
    return $value
  }
  return Join-Path $BaseRoot ($value -replace '/', '\')
}

# ----------------------------
# Rail execution
# ----------------------------
function Run-RailA {
  param([Parameter(Mandatory=$true)][string]$LogPath, $Plan)

  $scriptPath = Join-Path $osRoot "tools\governance\rails\run_rail_A.ps1"
  if ($Plan -and $Plan.railA -and $Plan.railA.script) {
    $scriptPath = Resolve-PlanPathValue -PathValue ([string]$Plan.railA.script) -BaseRoot $osRoot
  }

  Start-Heartbeat -Phase "rail_A" -LogPath $LogPath -IntervalSec $HeartbeatSec
  try {
    Write-PhaseMarker -PhaseId "A" -Kind "start" -Dir $RailsDir
    $exit = Run-Cmd -Name "rail_A" -FilePath "powershell" -Args @("-NoProfile","-ExecutionPolicy","Bypass","-File",$scriptPath) -LogPath $LogPath
    Write-PhaseMarker -PhaseId "A" -Kind "done" -Dir $RailsDir -Extra ("EXIT={0}" -f $exit)
    if ($exit -ne 0) { throw "Rail A failed: EXIT=$exit" }
  }
  finally {
    Stop-Heartbeat -LogPath $LogPath -Silent
  }
}

function Run-RailB {
  param([Parameter(Mandatory=$true)][string]$LogPath, $Plan, [string]$ResumeFrom)

  $workersDir = Join-Path $osRoot "tools\governance\workers"
  if ($Plan -and $Plan.railB -and $Plan.railB.workersDir) {
    $workersDir = Resolve-PlanPathValue -PathValue ([string]$Plan.railB.workersDir) -BaseRoot $osRoot
  }

  $phases = @("B1","B2","B3","B4","B5")
  if ($Plan -and $Plan.railB -and $Plan.railB.phases) { $phases = @($Plan.railB.phases) }

  $resumeFound = [string]::IsNullOrWhiteSpace($ResumeFrom)

  foreach ($ph in $phases) {
    if (-not $resumeFound) {
      if ($ph -eq $ResumeFrom) { $resumeFound = $true }
      else {
        Log-Line ("[rail] PHASE_SKIP {0}" -f $ph) $LogPath
        continue
      }
    }

    $worker = Join-Path $workersDir ("promote_stream_processing_{0}.py" -f $ph)
    if (-not (Test-Path $worker)) { throw "Missing Rail B worker: $worker" }

    Start-Heartbeat -Phase $ph -LogPath $LogPath -IntervalSec $HeartbeatSec
    try {
      Log-Line ("[rail] PHASE_START {0}" -f $ph) $LogPath
      Write-PhaseMarker -PhaseId $ph -Kind "start" -Dir $RailsDir
      $exit = Run-Cmd -Name $ph -FilePath $script:pythonInvocation.file_path -Args @($script:pythonInvocation.args_prefix + $worker) -LogPath $LogPath
      Write-PhaseMarker -PhaseId $ph -Kind "done" -Dir $RailsDir -Extra ("EXIT={0}" -f $exit)
      Log-Line ("[rail] PHASE_DONE {0} EXIT={1}" -f $ph,$exit) $LogPath
      if ($exit -ne 0) { throw "Rail B phase failed: $ph EXIT=$exit" }
    }
    finally {
      Stop-Heartbeat -LogPath $LogPath -Silent
    }
  }
}

function Run-RailC {
  param([Parameter(Mandatory=$true)][string]$LogPath, $Plan)

  $scriptPath = Join-Path $osRoot "tools\governance\rails\run_rail_C.ps1"
  if ($Plan -and $Plan.railC -and $Plan.railC.script) {
    $scriptPath = Resolve-PlanPathValue -PathValue ([string]$Plan.railC.script) -BaseRoot $osRoot
  }

  Start-Heartbeat -Phase "rail_C" -LogPath $LogPath -IntervalSec $HeartbeatSec
  try {
    Write-PhaseMarker -PhaseId "C" -Kind "start" -Dir $RailsDir
    $exit = Run-Cmd -Name "rail_C" -FilePath "powershell" -Args @("-NoProfile","-ExecutionPolicy","Bypass","-File",$scriptPath) -LogPath $LogPath
    Write-PhaseMarker -PhaseId "C" -Kind "done" -Dir $RailsDir -Extra ("EXIT={0}" -f $exit)
    if ($exit -ne 0) { throw "Rail C failed: EXIT=$exit" }
  }
  finally {
    Stop-Heartbeat -LogPath $LogPath -Silent
  }
}

# ----------------------------
# SelfTest: parse + basic sanity only (no edits)
# ----------------------------
if ($SelfTest) {
  try {
    $me = $MyInvocation.MyCommand.Path
    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($me, [ref]$tokens, [ref]$errors) | Out-Null

    if ($errors -and $errors.Count -gt 0) {
      $errors | ForEach-Object { Add-Content -Path $SelfTestLog -Value ("PARSE_ERROR: {0}" -f $_.Message) }
      "RUNNER_SELFTEST_EXIT=2" | Out-File -FilePath $SelfTestLog -Append
      exit 2
    }

    "RUNNER_SELFTEST_EXIT=0" | Out-File -FilePath $SelfTestLog
    exit 0
  }
  catch {
    ("RUNNER_SELFTEST_EXIT=1 {0}" -f $_.Exception.Message) | Out-File -FilePath $SelfTestLog
    exit 1
  }
}

# ----------------------------
# Main
# ----------------------------
$plan = Load-Plan -Path $PlanPath
Run-Preflight -LogPath $RunLog

try {
  if ($Rails -eq "ALL" -or $Rails -eq "A") { Run-RailA -LogPath $RunLog -Plan $plan }
  if ($Rails -eq "ALL" -or $Rails -eq "B") { Run-RailB -LogPath $RunLog -Plan $plan -ResumeFrom $ResumeFromPhase }
  if ($Rails -eq "ALL" -or $Rails -eq "C") { Run-RailC -LogPath $RunLog -Plan $plan }

  Log-Line "[rail] RUN_DONE EXIT=0" $RunLog
  exit 0
}
catch {
  Log-Line ("[rail] RUN_FAIL error={0}" -f $_.Exception.Message) $RunLog
  exit 1
}
finally {
  Stop-Heartbeat -LogPath $RunLog -Silent
}
