param(
  [string]$Version = "0.1.0",
  [string]$OsBase = "",
  [string]$FwBase = "",
  [string]$OutRoot = "",
  [switch]$IncludeFirmwareRewriteArtifacts = $true
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\common\pathing.ps1")

if([string]::IsNullOrWhiteSpace($OsBase)){
  $OsBase = Get-AxionOsRoot -ScriptPath $PSCommandPath
}
if([string]::IsNullOrWhiteSpace($FwBase)){
  $FwBase = Get-AxionFwBase -OsRoot $OsBase
}
if([string]::IsNullOrWhiteSpace($OutRoot)){
  $OutRoot = Join-Path $OsBase "out\full_install_bundle"
}
Enable-AxionLocalRuntimePath -OsRoot $OsBase
$pythonInvocation = Get-AxionPythonInvocation -OsRoot $OsBase

$complianceScript = Join-Path $PSScriptRoot "validate_third_party_bundle_compliance.py"
& $pythonInvocation.file_path @($pythonInvocation.args_prefix + @($complianceScript, '--os-root', $OsBase))
if($LASTEXITCODE -ne 0){
  throw "Third-party bundle compliance validation failed."
}
$complianceLatestJson = Join-Path $OsBase "out\packaging\third_party_bundle_compliance_latest.json"
$complianceLatestMd = Join-Path $OsBase "out\packaging\third_party_bundle_compliance_latest.md"

$releaseDir = Join-Path $OsBase ("out\release\{0}" -f $Version)
$unifiedRoot = Join-Path $OsBase ("out\unified_bundle\AxionStack-{0}" -f $Version)
$buildUnifiedScript = Join-Path $PSScriptRoot "build_unified_axion_stack_bundle.ps1"

if(-not (Test-Path $unifiedRoot)){
  if(-not (Test-Path $buildUnifiedScript)){
    throw "Missing unified bundle script: $buildUnifiedScript"
  }
  & $buildUnifiedScript -FwBase $FwBase -OsBase $OsBase -Version $Version
  if($LASTEXITCODE -ne 0){
    throw "Failed to build unified bundle for version $Version"
  }
}

$bootEfi = Join-Path $OsBase "build\boot\BOOTX64.EFI"
$kernelElf = Join-Path $OsBase "build\kernel\axion.elf"
$diskImg = Join-Path $OsBase "build\disk.img"
$fwCode = Join-Path $FwBase "out\OVMF_CODE.fd"
$fwVars = Join-Path $FwBase "out\OVMF_VARS.fd"
$fwMono = Join-Path $FwBase "out\OVMF.fd"

$required = @($bootEfi, $kernelElf, $diskImg, $releaseDir, $unifiedRoot)
foreach($item in $required){
  if(-not (Test-Path $item)){
    throw "Missing required build/install artifact: $item"
  }
}

$firmwareMode = ""
if((Test-Path $fwCode) -and (Test-Path $fwVars)){
  $firmwareMode = "split"
} elseif(Test-Path $fwMono){
  $firmwareMode = "monolithic"
} else {
  throw "Missing firmware payload under $FwBase\out (need OVMF_CODE.fd+OVMF_VARS.fd or OVMF.fd)"
}

$bundleRoot = Join-Path $OutRoot ("AxionStack-FullInstall-{0}" -f $Version)
if(Test-Path $bundleRoot){ Remove-Item $bundleRoot -Recurse -Force }

$dirs = @(
  "EFI\BOOT",
  "kernel",
  "boot",
  "installer\unified",
  "firmware",
  "manifests",
  "compliance",
  "scripts",
  "qa"
)
foreach($d in $dirs){
  New-Item -ItemType Directory -Force -Path (Join-Path $bundleRoot $d) | Out-Null
}

Copy-Item $bootEfi (Join-Path $bundleRoot "EFI\BOOT\BOOTX64.EFI") -Force
Copy-Item $kernelElf (Join-Path $bundleRoot "kernel\axion.elf") -Force
Copy-Item $diskImg (Join-Path $bundleRoot "boot\disk.img") -Force
Copy-Item (Join-Path $unifiedRoot "*") (Join-Path $bundleRoot "installer\unified") -Recurse -Force

if($firmwareMode -eq "split"){
  Copy-Item $fwCode (Join-Path $bundleRoot "firmware\OVMF_CODE.fd") -Force
  Copy-Item $fwVars (Join-Path $bundleRoot "firmware\OVMF_VARS.fd") -Force
} else {
  Copy-Item $fwMono (Join-Path $bundleRoot "firmware\OVMF.fd") -Force
}

$fwHandoff = Join-Path $FwBase "out\handoff\firmware_os_handoff_v1.json"
$fwPendingBios = Join-Path $FwBase "out\handoff\pending_bios_settings_v1.json"
$osManifest = Join-Path $releaseDir "manifest.json"
$osHashes = Join-Path $releaseDir "sha256sums.txt"
$gateSummary = Get-ChildItem -Path (Join-Path $OsBase "out\qa") -Filter "os_release_gate_*.json" -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if(Test-Path $osManifest){ Copy-Item $osManifest (Join-Path $bundleRoot "manifests\os_manifest.json") -Force }
if(Test-Path $osHashes){ Copy-Item $osHashes (Join-Path $bundleRoot "manifests\os_sha256sums.txt") -Force }
if(Test-Path $fwHandoff){ Copy-Item $fwHandoff (Join-Path $bundleRoot "manifests\firmware_os_handoff_v1.json") -Force }
if(Test-Path $fwPendingBios){ Copy-Item $fwPendingBios (Join-Path $bundleRoot "manifests\pending_bios_settings_v1.json") -Force }
if($null -ne $gateSummary){ Copy-Item $gateSummary.FullName (Join-Path $bundleRoot "qa\release_gate_summary.json") -Force }
if(Test-Path $complianceLatestJson){ Copy-Item $complianceLatestJson (Join-Path $bundleRoot "compliance\third_party_bundle_compliance_latest.json") -Force }
if(Test-Path $complianceLatestMd){ Copy-Item $complianceLatestMd (Join-Path $bundleRoot "compliance\third_party_bundle_compliance_latest.md") -Force }

$fwManifestRoot = Join-Path $FwBase "out\manifests"
if(Test-Path $fwManifestRoot){
  New-Item -ItemType Directory -Force -Path (Join-Path $bundleRoot "manifests\firmware") | Out-Null
  Copy-Item (Join-Path $fwManifestRoot "*") (Join-Path $bundleRoot "manifests\firmware") -Recurse -Force
}

$fwRewriteRoot = Join-Path $FwBase "out\rewrite"
if($IncludeFirmwareRewriteArtifacts -and (Test-Path $fwRewriteRoot)){
  New-Item -ItemType Directory -Force -Path (Join-Path $bundleRoot "firmware\rewrite") | Out-Null
  Copy-Item (Join-Path $fwRewriteRoot "*") (Join-Path $bundleRoot "firmware\rewrite") -Recurse -Force
}

$runner = @"
param(
  [string]`$TargetRoot = 'C:\AxionInstallTarget',
  [switch]`$ApplyFirmwarePayload
)

`$ErrorActionPreference = 'Stop'
`$bundleRoot = Split-Path -Parent `$PSScriptRoot
`$dest = Join-Path `$TargetRoot 'AxionStack-FullInstall-$Version'
`$unified = Join-Path `$bundleRoot 'installer\unified'
`$diskImage = Join-Path `$bundleRoot 'boot\disk.img'
`$firmware = Join-Path `$bundleRoot 'firmware'

New-Item -ItemType Directory -Force -Path `$dest | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path `$dest 'installer\unified') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path `$dest 'boot') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path `$dest 'firmware') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path `$dest 'manifests') | Out-Null

Copy-Item (Join-Path `$unified '*') (Join-Path `$dest 'installer\unified') -Recurse -Force
Copy-Item `$diskImage (Join-Path `$dest 'boot\disk.img') -Force
if(Test-Path (Join-Path `$bundleRoot 'manifests\*')){
  Copy-Item (Join-Path `$bundleRoot 'manifests\*') (Join-Path `$dest 'manifests') -Recurse -Force
}
if(`$ApplyFirmwarePayload){
  Copy-Item (Join-Path `$firmware '*') (Join-Path `$dest 'firmware') -Recurse -Force
}

Write-Host ("FULL_INSTALL_STAGED:{0}" -f `$dest)
Write-Host "Firmware flashing is not performed by this script; firmware payload is staged for controlled install flow."
"@
Set-Content -Path (Join-Path $bundleRoot "scripts\run_unified_install.ps1") -Value $runner -Encoding UTF8

$utcNow = (Get-Date).ToUniversalTime().ToString("o")
$files = Get-ChildItem $bundleRoot -Recurse -File | Where-Object { $_.Name -notin @("full_install_manifest.json","sha256sums.txt") }
$hashLines = @()
$artifacts = @()
foreach($f in $files){
  $h = (Get-FileHash -Path $f.FullName -Algorithm SHA256).Hash.ToLower()
  $rel = $f.FullName.Substring($bundleRoot.Length + 1).Replace("\","/")
  $hashLines += "$h *$rel"
  $artifacts += [ordered]@{
    path = $rel
    sha256 = $h
    size = $f.Length
  }
}

$bundleManifest = [ordered]@{
  product = "AxionStack"
  package_kind = "full_install_bundle"
  version = $Version
  created_utc = $utcNow
  os_base = $OsBase
  firmware_base = $FwBase
  source_release_dir = $releaseDir
  source_unified_dir = $unifiedRoot
  firmware_payload_mode = $firmwareMode
  includes_firmware_rewrite_artifacts = [bool]$IncludeFirmwareRewriteArtifacts
  boot_entry = "EFI/BOOT/BOOTX64.EFI"
  kernel_entry = "kernel/axion.elf"
  os_disk_image = "boot/disk.img"
  installer_runner = "scripts/run_unified_install.ps1"
  artifacts = $artifacts
  compliance = @{
    third_party_bundle_report = "compliance/third_party_bundle_compliance_latest.json"
  }
  notes = @(
    "Full install media bundle for live test execution.",
    "Firmware payload is included; autonomous firmware flashing is intentionally not executed by default."
  )
}

$manifestPath = Join-Path $bundleRoot "full_install_manifest.json"
$hashPath = Join-Path $bundleRoot "sha256sums.txt"
$bundleManifest | ConvertTo-Json -Depth 12 | Set-Content -Path $manifestPath -Encoding UTF8
$hashLines | Set-Content -Path $hashPath -Encoding UTF8

$zipPath = Join-Path $OutRoot ("AxionStack-FullInstall-{0}.zip" -f $Version)
if(Test-Path $zipPath){ Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $bundleRoot "*") -DestinationPath $zipPath -Force

Write-Output "FULL_INSTALL_BUNDLE_ROOT:$bundleRoot"
Write-Output "FULL_INSTALL_BUNDLE_ZIP:$zipPath"
Write-Output "FULL_INSTALL_MANIFEST:$manifestPath"
Write-Output "FULL_INSTALL_HASHES:$hashPath"
