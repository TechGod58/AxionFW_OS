param(
  [string]$Version = "0.1.0",
  [string]$OutRoot = "",
  [string]$BuildProfile = "dev",
  [string]$SourceRoot = ""
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\pathing.ps1')

if([string]::IsNullOrWhiteSpace($SourceRoot)){
  $SourceRoot = Get-AxionOsRoot -ScriptPath $PSCommandPath
}
Enable-AxionLocalRuntimePath -OsRoot $SourceRoot
$pythonInvocation = Get-AxionPythonInvocation -OsRoot $SourceRoot
if([string]::IsNullOrWhiteSpace($OutRoot)){
  $OutRoot = Join-Path $SourceRoot 'out\release'
}

function Get-CmdOutputOrNull([string]$cmd, [string[]]$cmdArgs){
  try {
    $out = & $cmd @cmdArgs 2>&1
    if($LASTEXITCODE -eq 0 -and $out){ return ($out | Select-Object -First 1 | ForEach-Object { $_.ToString().Trim() }) }
  } catch {}
  return $null
}

$utcNow = (Get-Date).ToUniversalTime().ToString('o')
$gitCommit = Get-CmdOutputOrNull 'git' @('-C', $SourceRoot, 'rev-parse', '--short', 'HEAD')
if(-not $gitCommit){ $gitCommit = 'nogit' }

$toolchain = [ordered]@{
  powershell = $PSVersionTable.PSVersion.ToString()
  git = (Get-CmdOutputOrNull 'git' @('--version'))
  python = (Get-CmdOutputOrNull $pythonInvocation.file_path @($pythonInvocation.args_prefix + '--version'))
}

$releaseDir = Join-Path $OutRoot $Version
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

$complianceScript = Join-Path $PSScriptRoot 'validate_third_party_bundle_compliance.py'
if(-not (Test-Path $complianceScript)){
  throw "Missing compliance validator: $complianceScript"
}
& $pythonInvocation.file_path @($pythonInvocation.args_prefix + @($complianceScript, '--os-root', $SourceRoot))
if($LASTEXITCODE -ne 0){
  throw "Third-party bundle compliance validation failed."
}
$complianceLatestJson = Join-Path $SourceRoot 'out\packaging\third_party_bundle_compliance_latest.json'
$complianceLatestMd = Join-Path $SourceRoot 'out\packaging\third_party_bundle_compliance_latest.md'

$dirs = @(
  'bin','config','assets\wallpapers','runtime\promotion','runtime\allocator','runtime\orchestrator_demo','runtime\shell_ui',
  'runtime\capsule\launchers','runtime\security','design','logs','qa','compliance'
)
foreach($d in $dirs){ New-Item -ItemType Directory -Force -Path (Join-Path $releaseDir $d) | Out-Null }

$copyMap = @(
  @{src=(Join-Path $SourceRoot 'config\SAFE_URI_POLICY_V1.json'); dst='config\SAFE_URI_POLICY_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\PROMOTION_POLICY_V1.json'); dst='config\PROMOTION_POLICY_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\APP_VM_ENFORCEMENT_V1.json'); dst='config\APP_VM_ENFORCEMENT_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\APP_COMPATIBILITY_ENVIRONMENTS_V1.json'); dst='config\APP_COMPATIBILITY_ENVIRONMENTS_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\COMPATIBILITY_LAYER_CATALOG_V1.json'); dst='config\COMPATIBILITY_LAYER_CATALOG_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\INSTALLER_COMPATIBILITY_MATRIX_V1.json'); dst='config\INSTALLER_COMPATIBILITY_MATRIX_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\SANDBOX_PROJECTION_POLICY_V1.json'); dst='config\SANDBOX_PROJECTION_POLICY_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\SANDBOX_PROJECTION_REGISTRY_V1.json'); dst='config\SANDBOX_PROJECTION_REGISTRY_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\SANDBOX_PROJECTION_SESSION_REGISTRY_V1.json'); dst='config\SANDBOX_PROJECTION_SESSION_REGISTRY_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\FIREWALL_GUARD_POLICY_V1.json'); dst='config\FIREWALL_GUARD_POLICY_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\FIREWALL_GUARD_STATE_V1.json'); dst='config\FIREWALL_GUARD_STATE_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\FIREWALL_QUARANTINE_REVIEW_V1.json'); dst='config\FIREWALL_QUARANTINE_REVIEW_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\KERNEL_NETWORK_SYSCALL_GUARD_V1.json'); dst='config\KERNEL_NETWORK_SYSCALL_GUARD_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\FIREWALL_CAPTURE_ADAPTERS_V1.json'); dst='config\FIREWALL_CAPTURE_ADAPTERS_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\WINDOWS_TOOLS_LAUNCH_MAP_V1.json'); dst='config\WINDOWS_TOOLS_LAUNCH_MAP_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\QM_ECC_POLICY_V1.json'); dst='config\QM_ECC_POLICY_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\QM_ECC_STATE_V1.json'); dst='config\QM_ECC_STATE_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\SYSTEM_PROGRAM_EXECUTION_POLICY_V1.json'); dst='config\SYSTEM_PROGRAM_EXECUTION_POLICY_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\SANDBOX_SHELL_CACHE_V1.json'); dst='config\SANDBOX_SHELL_CACHE_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\PROGRAM_MODULE_CATALOG_V1.json'); dst='config\PROGRAM_MODULE_CATALOG_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\program_layout.json'); dst='config\program_layout.json'},
  @{src=(Join-Path $SourceRoot 'config\SHELL_CONTEXT_MENU_V1.json'); dst='config\SHELL_CONTEXT_MENU_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\SHELL_DESKTOP_DEFAULTS_V1.json'); dst='config\SHELL_DESKTOP_DEFAULTS_V1.json'},
  @{src=(Join-Path $SourceRoot 'config\TOGGLES_STATE_V1.json'); dst='config\TOGGLES_STATE_V1.json'},
  @{src=(Join-Path $SourceRoot 'assets\wallpapers\wallpaper_index.json'); dst='assets\wallpapers\wallpaper_index.json'},
  @{src=(Join-Path $SourceRoot 'assets\wallpapers\WALLPAPERS.md'); dst='assets\wallpapers\WALLPAPERS.md'},
  @{src=(Join-Path $SourceRoot 'runtime\promotion\promoted.py'); dst='runtime\promotion\promoted.py'},
  @{src=(Join-Path $SourceRoot 'runtime\allocator\allocator.py'); dst='runtime\allocator\allocator.py'},
  @{src=(Join-Path $SourceRoot 'runtime\orchestrator_demo\run_e2e_demo.py'); dst='runtime\orchestrator_demo\run_e2e_demo.py'},
  @{src=(Join-Path $SourceRoot 'design\PHASE_2_CLOSEOUT_REPORT.md'); dst='design\PHASE_2_CLOSEOUT_REPORT.md'},
  @{src=(Join-Path $SourceRoot 'out\qa\phase2_shell_smoke_summary.json'); dst='qa\phase2_shell_smoke_summary.json'},
  @{src=(Join-Path $SourceRoot 'out\qa\phase2_shell_smoke_summary.md'); dst='qa\phase2_shell_smoke_summary.md'}
)
foreach($m in $copyMap){ if(Test-Path $m.src){ Copy-Item $m.src (Join-Path $releaseDir $m.dst) -Force } }
if(Test-Path $complianceLatestJson){ Copy-Item $complianceLatestJson (Join-Path $releaseDir 'compliance\third_party_bundle_compliance_latest.json') -Force }
if(Test-Path $complianceLatestMd){ Copy-Item $complianceLatestMd (Join-Path $releaseDir 'compliance\third_party_bundle_compliance_latest.md') -Force }

Get-ChildItem (Join-Path $SourceRoot 'assets\wallpapers') -Filter *.jpg -ErrorAction SilentlyContinue | ForEach-Object {
  Copy-Item $_.FullName (Join-Path $releaseDir ('assets\wallpapers\' + $_.Name)) -Force
}

$srcShell = Join-Path $SourceRoot 'runtime\shell_ui'
$dstShell = Join-Path $releaseDir 'runtime\shell_ui'
if(Test-Path $srcShell){
  Get-ChildItem $srcShell -Directory | ForEach-Object {
    $name = $_.Name
    New-Item -ItemType Directory -Force -Path (Join-Path $dstShell $name) | Out-Null
    Copy-Item "$($_.FullName)\*" (Join-Path $dstShell $name) -Recurse -Force
  }
}

$runtimeCopyDirs = @('runtime\capsule\launchers', 'runtime\security', 'runtime\qm')
foreach($rel in $runtimeCopyDirs){
  $src = Join-Path $SourceRoot $rel
  $dst = Join-Path $releaseDir $rel
  if(Test-Path $src){
    New-Item -ItemType Directory -Force -Path $dst | Out-Null
    Copy-Item "$src\*" $dst -Recurse -Force
  }
}

$files = Get-ChildItem $releaseDir -Recurse -File | Where-Object { $_.Name -ne 'manifest.json' -and $_.Name -ne 'sha256sums.txt' }
$hashLines = @(); $artifacts = @()
foreach($f in $files){
  $h = (Get-FileHash -Path $f.FullName -Algorithm SHA256).Hash.ToLower()
  $rel = $f.FullName.Substring($releaseDir.Length+1).Replace('\\','/')
  $hashLines += "$h *$rel"
  $artifacts += [ordered]@{path=$rel; sha256=$h; size=$f.Length; build_profile=$BuildProfile; build_utc=$utcNow}
}
$hashPath = Join-Path $releaseDir 'sha256sums.txt'
$hashLines | Set-Content -Path $hashPath -Encoding UTF8

$qa = @{ shell_smoke = @{ passed = $null; failed = $null } }
$qaJson = Join-Path $releaseDir 'qa\phase2_shell_smoke_summary.json'
if(Test-Path $qaJson){
  $q = Get-Content $qaJson -Raw | ConvertFrom-Json
  $qa.shell_smoke.passed = $q.passed
  $qa.shell_smoke.failed = $q.failed
}

$manifest = [ordered]@{
  product='AxionOS'
  edition='Qh8#'
  version=$Version
  build_id=("{0}-{1}-{2}" -f $Version, $BuildProfile, $gitCommit)
  build_utc=$utcNow
  build_profile=$BuildProfile
  source_commit=$gitCommit
  toolchain=$toolchain
  channel='dev'
  qa=$qa
  packaging_compliance = @{
    third_party_bundle_report = 'compliance/third_party_bundle_compliance_latest.json'
    third_party_bundle_ok = (Test-Path (Join-Path $releaseDir 'compliance\third_party_bundle_compliance_latest.json'))
  }
  artifacts=$artifacts
  notes='Release scaffold with deterministic build metadata (commit/toolchain/profile/utc) and artifact metadata.'
}
$manifestPath = Join-Path $releaseDir 'manifest.json'
$manifest | ConvertTo-Json -Depth 10 | Set-Content -Path $manifestPath -Encoding UTF8

Write-Output "RELEASE_BUILT:$releaseDir"
Write-Output "MANIFEST:$manifestPath"
Write-Output "HASHES:$hashPath"
Write-Output "BUILD_ID:$($manifest.build_id)"
