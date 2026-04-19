param(
  [string]$OutRoot = "",
  [switch]$TryElevatedCollector,
  [switch]$EnableRewritePlanner = $true,
  [switch]$EnableRewriteExecution
)

$ErrorActionPreference = 'Stop'

$baseRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($OutRoot)) {
  $OutRoot = Join-Path $baseRoot 'out'
}
New-Item -ItemType Directory -Force -Path $OutRoot | Out-Null

$invArgs = @(
  '-NoProfile',
  '-ExecutionPolicy', 'Bypass',
  '-File', (Join-Path $PSScriptRoot '10_probe_hardware.ps1')
)
if ($TryElevatedCollector) {
  $invArgs += '-TryElevatedCollector'
}
$inv = & powershell @invArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$plan = & py -3 (Join-Path $PSScriptRoot '20_policy_plan.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$handoff = & py -3 (Join-Path $PSScriptRoot '30_emit_os_handoff.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$rewriteGraph = ""
$rewritePlan = ""
$rewriteExec = ""
if($EnableRewritePlanner){
  $rewriteGraph = & py -3 (Join-Path $PSScriptRoot '50_build_hardware_capability_graph.py')
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  $rewritePlan = & py -3 (Join-Path $PSScriptRoot '60_plan_signed_rewrite.py')
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  if($EnableRewriteExecution){
    $rewriteExec = & py -3 (Join-Path $PSScriptRoot '70_execute_signed_rewrite.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
}

$result = [ordered]@{
  ok = $true
  code = 'AXION_FW_POLICY_PIPELINE_READY'
  inventory = ($inv | Out-String).Trim()
  plan = ($plan | Out-String).Trim()
  handoff = ($handoff | Out-String).Trim()
  rewrite_capability_graph = ($rewriteGraph | Out-String).Trim()
  rewrite_plan_signed = ($rewritePlan | Out-String).Trim()
  rewrite_execution = ($rewriteExec | Out-String).Trim()
}

$result | ConvertTo-Json -Depth 8
