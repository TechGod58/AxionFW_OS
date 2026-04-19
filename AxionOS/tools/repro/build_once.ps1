param(
  [string]$Version = '0.1.0',
  [string]$BuildProfile = 'dev',
  [string]$OsBase = ''
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\pathing.ps1')

if([string]::IsNullOrWhiteSpace($OsBase)){
  $OsBase = Get-AxionOsRoot -ScriptPath $PSCommandPath
}

$script = Join-Path $OsBase 'tools\packaging\build_release.ps1'
if(-not (Test-Path $script)){ throw "Missing build script: $script" }

& powershell -ExecutionPolicy Bypass -File $script -Version $Version -BuildProfile $BuildProfile -SourceRoot $OsBase
if($LASTEXITCODE -ne 0){ throw "build_release failed with exit code $LASTEXITCODE" }

Write-Output ("REPRO_BUILD_OK:{0}:{1}" -f $Version, $BuildProfile)
