param(
  [Parameter(Mandatory = $true)]
  [string]$DriveLetter,
  [string]$Version = "0.1.0",
  [string]$OsBase = "",
  [string]$FullBundleRoot = "",
  [switch]$PreserveExistingContent = $true
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\common\pathing.ps1")

if([string]::IsNullOrWhiteSpace($OsBase)){
  $OsBase = Get-AxionOsRoot -ScriptPath $PSCommandPath
}

$dl = ($DriveLetter.Trim().TrimEnd('\').TrimEnd(':')).ToUpperInvariant()
if([string]::IsNullOrWhiteSpace($dl) -or $dl.Length -ne 1){
  throw "DriveLetter must be a single drive letter like E"
}
$targetRoot = "{0}:\" -f $dl
$resolvedTarget = (Resolve-Path $targetRoot).Path
if($resolvedTarget -ne $targetRoot){
  throw "Resolved target mismatch. Expected $targetRoot got $resolvedTarget"
}

$volume = Get-Volume -DriveLetter $dl -ErrorAction Stop
if($volume.DriveType -ne "Removable"){
  throw "Refusing to write boot media to non-removable drive $targetRoot (DriveType=$($volume.DriveType))"
}

if([string]::IsNullOrWhiteSpace($FullBundleRoot)){
  $FullBundleRoot = Join-Path $OsBase ("out\full_install_bundle\AxionStack-FullInstall-{0}" -f $Version)
}
if(-not (Test-Path $FullBundleRoot)){
  $builder = Join-Path $PSScriptRoot "build_full_install_bundle.ps1"
  if(-not (Test-Path $builder)){
    throw "Missing full bundle builder script: $builder"
  }
  & $builder -Version $Version -OsBase $OsBase
  if($LASTEXITCODE -ne 0){
    throw "Failed building full install bundle for $Version"
  }
}
if(-not (Test-Path $FullBundleRoot)){
  throw "Full install bundle missing: $FullBundleRoot"
}

$bootSrc = Join-Path $FullBundleRoot "EFI\BOOT\BOOTX64.EFI"
$kernelSrc = Join-Path $FullBundleRoot "kernel\axion.elf"
if(-not (Test-Path $bootSrc)){ throw "Missing boot loader in full bundle: $bootSrc" }
if(-not (Test-Path $kernelSrc)){ throw "Missing kernel in full bundle: $kernelSrc" }

$efiBootDir = Join-Path $targetRoot "EFI\BOOT"
$kernelDir = Join-Path $targetRoot "kernel"
$payloadDir = Join-Path $targetRoot "AxionFullInstall"

if(-not $PreserveExistingContent){
  foreach($p in @($efiBootDir, $kernelDir, $payloadDir, (Join-Path $targetRoot "RUN_AXION_FULL_INSTALL.ps1"), (Join-Path $targetRoot "START_HERE_AXION_FULL_INSTALL.txt"))){
    if(Test-Path $p){ Remove-Item $p -Recurse -Force }
  }
}

New-Item -ItemType Directory -Force -Path $efiBootDir | Out-Null
New-Item -ItemType Directory -Force -Path $kernelDir | Out-Null
if(Test-Path $payloadDir){ Remove-Item $payloadDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $payloadDir | Out-Null

Copy-Item $bootSrc (Join-Path $efiBootDir "BOOTX64.EFI") -Force
Copy-Item $kernelSrc (Join-Path $kernelDir "axion.elf") -Force
Copy-Item (Join-Path $FullBundleRoot "*") $payloadDir -Recurse -Force

$launcher = @"
param(
  [string]`$TargetRoot = 'C:\AxionInstallTarget',
  [switch]`$ApplyFirmwarePayload
)

`$ErrorActionPreference = 'Stop'
`$runner = Join-Path `$PSScriptRoot 'AxionFullInstall\scripts\run_unified_install.ps1'
if(-not (Test-Path `$runner)){ throw "Missing bundle runner: `$runner" }
& `$runner -TargetRoot `$TargetRoot -ApplyFirmwarePayload:`$ApplyFirmwarePayload
"@
Set-Content -Path (Join-Path $targetRoot "RUN_AXION_FULL_INSTALL.ps1") -Value $launcher -Encoding UTF8

$readme = @"
Axion Full Install USB (OS + Firmware Payload)

This USB is prepared as UEFI bootable:
- EFI\BOOT\BOOTX64.EFI
- kernel\axion.elf

Full install payload:
- AxionFullInstall\

Live-test path:
1) Boot target machine from this USB in UEFI mode.
2) Boot chain loads Axion from \kernel\axion.elf.
3) Use payload in \AxionFullInstall for unified install flow.

From Windows host (staging action):
- .\RUN_AXION_FULL_INSTALL.ps1

Note:
- This media includes firmware payload artifacts.
- Autonomous motherboard flashing is not executed by default.
"@
Set-Content -Path (Join-Path $targetRoot "START_HERE_AXION_FULL_INSTALL.txt") -Value $readme -Encoding UTF8

Write-Output "USB_TARGET:$targetRoot"
Write-Output "USB_BOOT_FILE:$efiBootDir\BOOTX64.EFI"
Write-Output "USB_KERNEL_FILE:$kernelDir\axion.elf"
Write-Output "USB_FULL_PAYLOAD:$payloadDir"
Write-Output "USB_LAUNCHER:$targetRoot`RUN_AXION_FULL_INSTALL.ps1"
Write-Output "USB_README:$targetRoot`START_HERE_AXION_FULL_INSTALL.txt"
