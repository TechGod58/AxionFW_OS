param(
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
$repoRoot = $PSScriptRoot
$osBase = Join-Path $repoRoot 'AxionOS'
$fwBase = Join-Path $repoRoot 'AxionFW\Base'

& (Join-Path $repoRoot 'tools\ensure_workspace_aliases.ps1') -RepoRoot $repoRoot
& (Join-Path $osBase 'tools\firmware\build_axion_stack.ps1') `
  -OsBase $osBase `
  -FwBase $fwBase `
  -Distro $Distro `
  -InstallDeps:$InstallDeps `
  -CleanOsBuild:$CleanOsBuild `
  -SkipFirmwareBuild:$SkipFirmwareBuild `
  -ReuseFirmwareIfPresent:$ReuseFirmwareIfPresent `
  -CleanFirmwareBuild:$CleanFirmwareBuild `
  -SyncFirmwareSubmodules:$SyncFirmwareSubmodules `
  -FirmwareBuildTarget $FirmwareBuildTarget `
  -FirmwareToolchain $FirmwareToolchain `
  -FirmwarePlatformDsc $FirmwarePlatformDsc `
  -FirmwareBuildTimeoutSeconds $FirmwareBuildTimeoutSeconds `
  -RunQemu:$RunQemu `
  -QemuTimeoutSeconds $QemuTimeoutSeconds
