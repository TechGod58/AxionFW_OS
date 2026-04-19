param(
  [string]$FwBase = '',
  [string]$OsBase = '',
  [string]$Version = '0.1.0',
  [string]$OutRoot = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\pathing.ps1')

if([string]::IsNullOrWhiteSpace($OsBase)){
  $OsBase = Get-AxionOsRoot -ScriptPath $PSCommandPath
}
if([string]::IsNullOrWhiteSpace($FwBase)){
  $FwBase = Get-AxionFwBase -OsRoot $OsBase
}
if([string]::IsNullOrWhiteSpace($OutRoot)){
  $OutRoot = Join-Path $OsBase 'out\unified_bundle'
}
Enable-AxionLocalRuntimePath -OsRoot $OsBase
$pythonInvocation = Get-AxionPythonInvocation -OsRoot $OsBase

$complianceScript = Join-Path $PSScriptRoot 'validate_third_party_bundle_compliance.py'
& $pythonInvocation.file_path @($pythonInvocation.args_prefix + @($complianceScript, '--os-root', $OsBase))
if($LASTEXITCODE -ne 0){
  throw "Third-party bundle compliance validation failed."
}
$complianceLatestJson = Join-Path $OsBase 'out\packaging\third_party_bundle_compliance_latest.json'
$complianceLatestMd = Join-Path $OsBase 'out\packaging\third_party_bundle_compliance_latest.md'

$fwCode = Join-Path $FwBase 'out\OVMF_CODE.fd'
$fwVars = Join-Path $FwBase 'out\OVMF_VARS.fd'
$fwMono = Join-Path $FwBase 'out\OVMF.fd'
$osRelease = Join-Path $OsBase ('out\release\' + $Version)
$bundleRoot = Join-Path $OutRoot ("AxionStack-{0}" -f $Version)

if(Test-Path $bundleRoot){ Remove-Item $bundleRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path $bundleRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $bundleRoot 'installer\firmware') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $bundleRoot 'installer\os') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $bundleRoot 'installer\drivers') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $bundleRoot 'profiles\boards') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $bundleRoot 'contracts') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $bundleRoot 'compliance') | Out-Null

if((Test-Path $fwCode) -and (Test-Path $fwVars)){
  Copy-Item $fwCode (Join-Path $bundleRoot 'installer\firmware\OVMF_CODE.fd') -Force
  Copy-Item $fwVars (Join-Path $bundleRoot 'installer\firmware\OVMF_VARS.fd') -Force
} elseif(Test-Path $fwMono) {
  Copy-Item $fwMono (Join-Path $bundleRoot 'installer\firmware\OVMF.fd') -Force
} else {
  throw "Missing AxionFW firmware artifacts under $FwBase\out"
}

if(-not (Test-Path $osRelease)){
  throw "Missing AxionOS release payload: $osRelease"
}
Copy-Item "$osRelease\*" (Join-Path $bundleRoot 'installer\os') -Recurse -Force

Copy-Item (Join-Path $OsBase 'config\AXION_HAL_PROFILE_V1.json') (Join-Path $bundleRoot 'contracts\AXION_HAL_PROFILE_V1.json') -Force
Copy-Item (Join-Path $OsBase 'config\BOARD_SUPPORT_PACKAGE_CATALOG_V1.json') (Join-Path $bundleRoot 'profiles\boards\BOARD_SUPPORT_PACKAGE_CATALOG_V1.json') -Force
Copy-Item (Join-Path $OsBase 'config\FIRMWARE_OS_HARDWARE_CONTRACT_V1.json') (Join-Path $bundleRoot 'contracts\FIRMWARE_OS_HARDWARE_CONTRACT_V1.json') -Force
if(Test-Path $complianceLatestJson){ Copy-Item $complianceLatestJson (Join-Path $bundleRoot 'compliance\third_party_bundle_compliance_latest.json') -Force }
if(Test-Path $complianceLatestMd){ Copy-Item $complianceLatestMd (Join-Path $bundleRoot 'compliance\third_party_bundle_compliance_latest.md') -Force }

$manifest = [ordered]@{
  product = 'AxionStack'
  version = $Version
  firmware_provider = 'AxionFW'
  os_provider = 'AxionOS'
  installer_order = @(
    'hardware_compatibility_gate',
    'firmware_install',
    'driver_bundle_install',
    'os_install',
    'security_seal_and_handoff'
  )
  created_utc = (Get-Date).ToUniversalTime().ToString('o')
  compliance = @{
    third_party_bundle_report = 'compliance/third_party_bundle_compliance_latest.json'
  }
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $bundleRoot 'unified_bundle_manifest.json') -Encoding UTF8

Write-Output "UNIFIED_BUNDLE_ROOT:$bundleRoot"
