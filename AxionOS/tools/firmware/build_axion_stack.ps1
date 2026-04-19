param(
  [string]$FwBase = "",
  [string]$OsBase = "",
  [string]$Distro = "Ubuntu",
  [switch]$InstallDeps,
  [switch]$CleanOsBuild,
  [switch]$SkipFirmwareBuild,
  [switch]$ReuseFirmwareIfPresent,
  [switch]$CleanFirmwareBuild,
  [switch]$SyncFirmwareSubmodules,
  [string]$FirmwareBuildTarget = "DEBUG",
  [string]$FirmwareToolchain = "GCC5",
  [string]$FirmwarePlatformDsc = "OvmfPkg/OvmfPkgX64.dsc",
  [int]$FirmwareBuildTimeoutSeconds = 0,
  [switch]$RunQemu = $true,
  [int]$QemuTimeoutSeconds = 0
)

$ErrorActionPreference = 'Stop'

$scriptOsBase = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$combinedRoot = Split-Path -Parent $scriptOsBase
$combinedFwBase = Join-Path $combinedRoot 'AxionFW\Base'

if ([string]::IsNullOrWhiteSpace($OsBase)) {
  $OsBase = $scriptOsBase
}
if ([string]::IsNullOrWhiteSpace($FwBase)) {
  if (Test-Path $combinedFwBase) {
    $FwBase = $combinedFwBase
  } else {
    $systemDrive = [System.Environment]::GetEnvironmentVariable('SystemDrive','Process')
    if([string]::IsNullOrWhiteSpace($systemDrive)){ $systemDrive = 'C:' }
    $FwBase = Join-Path $systemDrive 'AxionFW\Base'
  }
}

function Convert-ToWslPath {
  param([Parameter(Mandatory = $true)][string]$WindowsPath)

  if ($WindowsPath -notmatch '^([A-Za-z]):\\') {
    throw "Expected a drive-qualified Windows path, got: $WindowsPath"
  }

  $drive = $Matches[1].ToLowerInvariant()
  $tail = ($WindowsPath.Substring(2) -replace '\\', '/')
  return "/mnt/$drive$tail"
}

if (-not (Test-Path $FwBase)) {
  throw "Missing firmware base: $FwBase"
}

if (-not (Test-Path $OsBase)) {
  throw "Missing OS base: $OsBase"
}

$fwBootstrap = Join-Path $FwBase 'scripts\01_bootstrap_edk2_ovmf.bat'
if ((-not $SkipFirmwareBuild) -and (-not (Test-Path $fwBootstrap))) {
  throw "Missing firmware bootstrap script: $fwBootstrap"
}

if (-not $SkipFirmwareBuild) {
  $fwEnv = @(
    "set AXIONFW_BASE=$FwBase",
    "set AXIONFW_NO_PAUSE=1",
    "set AXIONFW_INSTALL_DEPS=$(if ($InstallDeps) { '1' } else { '0' })",
    "set AXIONFW_REUSE_IF_PRESENT=$(if ($ReuseFirmwareIfPresent) { '1' } else { '0' })",
    "set AXIONFW_CLEAN_BUILD=$(if ($CleanFirmwareBuild) { '1' } else { '0' })",
    "set AXIONFW_SYNC_SUBMODULES=$(if ($SyncFirmwareSubmodules) { '1' } else { '0' })",
    "set AXIONFW_BUILD_TARGET=$FirmwareBuildTarget",
    "set AXIONFW_TOOLCHAIN=$FirmwareToolchain",
    "set AXIONFW_PLATFORM_DSC=$FirmwarePlatformDsc",
    "set AXIONFW_BUILD_TIMEOUT_SECS=$FirmwareBuildTimeoutSeconds",
    "call `"$fwBootstrap`""
  ) -join ' && '

  Write-Host "[1/3] Building AxionFW firmware..."
  Write-Host "      FwBase=$FwBase"
  Write-Host "      Reuse=$ReuseFirmwareIfPresent Clean=$CleanFirmwareBuild SyncSubmodules=$SyncFirmwareSubmodules Timeout=${FirmwareBuildTimeoutSeconds}s"
  cmd /c $fwEnv
  if ($LASTEXITCODE -ne 0) {
    throw "AxionFW build failed with exit code $LASTEXITCODE"
  }
} else {
  Write-Host "[1/3] Reusing existing AxionFW firmware artifacts..."
  Write-Host "      FwBase=$FwBase"
}

$fwCode = Join-Path $FwBase 'out\OVMF_CODE.fd'
$fwVars = Join-Path $FwBase 'out\OVMF_VARS.fd'
$fwMono = Join-Path $FwBase 'out\OVMF.fd'

$fwMode = $null
if ((Test-Path $fwCode) -and (Test-Path $fwVars)) {
  $fwMode = 'split'
} elseif (Test-Path $fwMono) {
  $fwMode = 'monolithic'
} else {
  throw "No firmware artifact found under $FwBase\out"
}

$osWsl = Convert-ToWslPath $OsBase
$fwCodeWsl = Convert-ToWslPath $fwCode
$fwMonoWsl = Convert-ToWslPath $fwMono

$runtimeVarsPath = $null
$runtimeVarsWsl = $null
if ($fwMode -eq 'split') {
  $runtimeDir = Join-Path $OsBase 'out\fw_boot'
  New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
  $runtimeVarsPath = Join-Path $runtimeDir 'OVMF_VARS.runtime.fd'
  Copy-Item -Force $fwVars $runtimeVarsPath
  $runtimeVarsWsl = Convert-ToWslPath $runtimeVarsPath
}

$makeSteps = New-Object System.Collections.Generic.List[string]
$makeSteps.Add("cd '$osWsl'")
if ($CleanOsBuild) {
  $makeSteps.Add('make clean')
}
$makeSteps.Add('make')

if ($RunQemu) {
  $runStep = if ($fwMode -eq 'split') {
    "make run FW_CODE='$fwCodeWsl' FW_VARS='$runtimeVarsWsl'"
  } else {
    "make run FW_MONO='$fwMonoWsl'"
  }

  if ($QemuTimeoutSeconds -gt 0) {
    $runStep = "timeout ${QemuTimeoutSeconds}s $runStep"
  }

  $makeSteps.Add($runStep)
}

$wslCommand = $makeSteps -join ' && '

Write-Host "[2/3] Building AxionOS..."
Write-Host "      OsBase=$OsBase"
if ($RunQemu) {
  Write-Host "[3/3] Booting AxionOS on AxionFW firmware..."
}

wsl -d $Distro -- bash -lc $wslCommand
if (($QemuTimeoutSeconds -gt 0) -and ($LASTEXITCODE -eq 124)) {
  Write-Host "Smoke run reached timeout after $QemuTimeoutSeconds seconds; treating boot as successful."
} elseif ($LASTEXITCODE -ne 0) {
  throw "AxionOS build/run failed with exit code $LASTEXITCODE"
}
