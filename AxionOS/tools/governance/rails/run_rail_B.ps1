
param(
  [string]$PlanPath = '',
  [string]$RunId = ''
)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\..\common\pathing.ps1')

$osRoot = Get-AxionOsRoot -ScriptPath $PSCommandPath
Enable-AxionLocalRuntimePath -OsRoot $osRoot
$pythonInvocation = Get-AxionPythonInvocation -OsRoot $osRoot
$rail='B'
if([string]::IsNullOrWhiteSpace($PlanPath)){
  $PlanPath = Join-Path $osRoot 'config\governance\rail_plan.json'
}
if(-not [System.IO.Path]::IsPathRooted($PlanPath)){
  $PlanPath = Join-Path $osRoot $PlanPath
}
if(-not (Test-Path $PlanPath)){ Write-Output "WRAPPER_FAIL rail=$rail reason=missing_plan path=$PlanPath"; exit 2 }
$plan = Get-Content -Raw -Path $PlanPath | ConvertFrom-Json
$target = $plan.rails | Where-Object { $_.rail_id -eq $rail } | Select-Object -First 1
if($null -eq $target){ Write-Output "WRAPPER_FAIL rail=$rail reason=rail_not_found"; exit 3 }
$out=Join-Path $osRoot 'out\governance\rails'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$ts = (Get-Date).ToUniversalTime().ToString('o')
Set-Content -Path (Join-Path $out ("rail_${rail}_timestamps.json")) -Value (@{started_utc=$ts;run_id=$RunId;plan=$PlanPath}|ConvertTo-Json -Depth 4) -Encoding UTF8

function Resolve-StepPath {
  param([string]$Value)
  if([string]::IsNullOrWhiteSpace($Value)){ return $Value }
  $legacyPrefix = 'C:\AxionOS'
  if($Value.StartsWith($legacyPrefix,[System.StringComparison]::OrdinalIgnoreCase)){
    $suffix = $Value.Substring($legacyPrefix.Length).TrimStart('\','/')
    if([string]::IsNullOrWhiteSpace($suffix)){ return $osRoot }
    return Join-Path $osRoot ($suffix -replace '/','\')
  }
  if([System.IO.Path]::IsPathRooted($Value)){ return $Value }
  return Join-Path $osRoot ($Value -replace '/','\')
}

foreach($phase in $target.phases){
  foreach($step in $phase.steps){
    $stepPath = Resolve-StepPath -Value ([string]$step.path)
    $cmd = @($stepPath) + @($step.args)
    Write-Output ("[wrapper] rail={0} phase={1} step={2}" -f $rail,$phase.phase_id,$step.name)
    & $pythonInvocation.file_path @($pythonInvocation.args_prefix + $cmd)
    if($LASTEXITCODE -ne 0){
      Set-Content -Path (Join-Path $out ("rail_${rail}_exit.txt")) -Value "$LASTEXITCODE" -Encoding ASCII
      Write-Output ("WRAPPER_FAIL rail={0} phase={1} step={2} exit={3}" -f $rail,$phase.phase_id,$step.name,$LASTEXITCODE)
      exit $LASTEXITCODE
    }
  }
}
$done=(Get-Date).ToUniversalTime().ToString('o')
Set-Content -Path (Join-Path $out ("rail_${rail}_exit.txt")) -Value '0' -Encoding ASCII
Set-Content -Path (Join-Path $out ("rail_${rail}_timestamps.json")) -Value (@{started_utc=$ts;ended_utc=$done;run_id=$RunId;plan=$PlanPath}|ConvertTo-Json -Depth 4) -Encoding UTF8
Write-Output ("WRAPPER_OK rail={0}" -f $rail)
exit 0

