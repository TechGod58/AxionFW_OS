param(
  [string]$Version = '0.1.0',
  [string]$BuildProfile = 'dev',
  [switch]$SkipReproBuild,
  [switch]$SkipQemuDryRun,
  [switch]$SkipGoldenDryRun,
  [switch]$EnableKernelLiveBoot,
  [switch]$RequireKernelLiveBoot,
  [string]$KernelLiveBootDistro = 'Ubuntu',
  [int]$KernelLiveBootTimeoutSec = 45,
  [switch]$EnableUnifiedStackSmoke,
  [switch]$RequireUnifiedStackSmoke,
  [int]$UnifiedStackQemuTimeoutSec = 20,
  [switch]$ResolveSigningFromKeyVault,
  [switch]$PromptForSigningKeys,
  [string]$SigningKeyVaultName = '',
  [string]$KmsSigningKeySecretName = '',
  [string]$HsmSigningKeySecretName = '',
  [string]$KmsSigningKeyFile = '',
  [string]$HsmSigningKeyFile = '',
  [switch]$EnableMlSidecar,
  [switch]$RequireMlSidecar,
  [switch]$EnforceMlSidecarAnomaly
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\pathing.ps1')
. (Join-Path $PSScriptRoot '..\common\signing_env.ps1')

$osRoot = Get-AxionOsRoot -ScriptPath $PSCommandPath
$repoRoot = Split-Path -Parent $osRoot
$stackScriptPath = Join-Path $repoRoot 'build_axion_stack.ps1'
$outDir = Join-Path $osRoot 'out\qa'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Enable-AxionLocalRuntimePath -OsRoot $osRoot
$pythonInvocation = Get-AxionPythonInvocation -OsRoot $osRoot

$signingResolution = Initialize-AxionReleaseSigningEnv `
  -UseKeyVault:$ResolveSigningFromKeyVault `
  -PromptIfMissing:$PromptForSigningKeys `
  -KeyVaultName $SigningKeyVaultName `
  -KmsSecretName $KmsSigningKeySecretName `
  -HsmSecretName $HsmSigningKeySecretName `
  -KmsKeyFile $KmsSigningKeyFile `
  -HsmKeyFile $HsmSigningKeyFile

$requiredSigningEnv = @('AXION_KMS_RELEASE_SIGNING_KEY_01', 'AXION_HSM_RELEASE_SIGNING_KEY_02')
$missingSigningEnv = @()
foreach($name in $requiredSigningEnv){
  $value = [Environment]::GetEnvironmentVariable($name, 'Process')
  if([string]::IsNullOrWhiteSpace($value)){
    $missingSigningEnv += $name
  }
}
if($missingSigningEnv.Count -gt 0){
  $resolutionTail = @($signingResolution.details | ForEach-Object { "{0}:{1}:{2}" -f $_.env_name, $_.source, $(if($_.error){$_.error}else{'ok'}) })
  throw ("Missing required provenance signing env vars: {0}. Inject these from your KMS/HSM source before running release gate. Resolver details: {1}" -f ($missingSigningEnv -join ', '), ($resolutionTail -join ' | '))
}

$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$summaryPath = Join-Path $outDir ("os_release_gate_{0}.json" -f $stamp)

function Invoke-Step {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][scriptblock]$Action
  )

  $start = Get-Date
  $output = @()
  $ok = $false
  $exitCode = 1

  try {
    $output = & $Action 2>&1
    $exitCode = $LASTEXITCODE
    $ok = ($exitCode -eq 0)
  } catch {
    $output += $_.Exception.Message
    $exitCode = 1
    $ok = $false
  }

  $end = Get-Date
  return [ordered]@{
    name = $Name
    ok = $ok
    exit_code = $exitCode
    started_utc = $start.ToUniversalTime().ToString('o')
    ended_utc = $end.ToUniversalTime().ToString('o')
    output_tail = @($output | ForEach-Object { $_.ToString() } | Select-Object -Last 20)
  }
}

function Read-JsonOrNull([string]$Path) {
  if(Test-Path $Path){
    return Get-Content -Path $Path -Raw | ConvertFrom-Json
  }
  return $null
}

$steps = @()
$checks = [ordered]@{}

$phase2SummaryPath = Join-Path $osRoot 'out\qa\phase2_shell_smoke_summary.json'
$shellSurfaceSummaryPath = Join-Path $osRoot 'out\qa\shell_surface_contract_smoke_summary.json'
$windowsToolsExecutionSummaryPath = Join-Path $osRoot 'out\qa\windows_tools_execution_smoke_summary.json'
$parallelCubedModeSummaryPath = Join-Path $osRoot 'out\qa\parallel_cubed_mode_smoke_summary.json'
$firmwareOsHandoffSummaryPath = Join-Path $osRoot 'out\runtime\firmware_os_handoff_enforcement_smoke.json'
$masterSummaryPath = Join-Path $osRoot 'out\qa\master_smoke_summary.json'
$securitySummaryPath = Join-Path $osRoot 'out\qa\security_core_smoke_summary.json'
$kernelPolicySummaryPath = Join-Path $osRoot 'out\qa\kernel_policy_contract_smoke_summary.json'
$kernelSubsystemSummaryPath = Join-Path $osRoot 'out\qa\kernel_subsystem_ownership_smoke_summary.json'
$kernelRuntimeSummaryPath = Join-Path $osRoot 'out\qa\kernel_runtime_ownership_smoke_summary.json'
$kernelExecutionDepthSummaryPath = Join-Path $osRoot 'out\qa\kernel_execution_depth_smoke_summary.json'
$compatModuleSummaryPath = Join-Path $osRoot 'out\qa\compatibility_module_smoke_summary.json'
$installerReplaySummaryPath = Join-Path $osRoot 'out\qa\installer_replay_matrix_smoke_summary.json'
$projectionSessionSummaryPath = Join-Path $osRoot 'out\qa\projection_session_smoke_summary.json'
$firewallQuarantineSummaryPath = Join-Path $osRoot 'out\qa\firewall_quarantine_adjudication_smoke_summary.json'
$operationalSoakSummaryPath = Join-Path $osRoot 'out\qa\operational_soak_recovery_smoke_summary.json'
$mediaEngineSummaryPath = Join-Path $osRoot 'out\qa\media_engine_contract_smoke_summary.json'
$mlSidecarSummaryPath = Join-Path $osRoot 'out\qa\ml_security_sidecar_report.json'
$fwSummaryPath = Join-Path $osRoot 'out\fw_gate\summary.json'
$goldenSummaryPath = Join-Path $osRoot ("out\smoke\golden_vm_smoke_{0}.json" -f $Version)
$runKernelLiveBoot = ($EnableKernelLiveBoot -or ($BuildProfile -eq 'release') -or $RequireKernelLiveBoot)
$runUnifiedStackSmoke = ($EnableUnifiedStackSmoke -or ($BuildProfile -eq 'release') -or $RequireUnifiedStackSmoke)
$runMlSidecar = ($EnableMlSidecar -or ($BuildProfile -eq 'release') -or $RequireMlSidecar)
$mlOriginalEnable = [Environment]::GetEnvironmentVariable('AXION_ENABLE_ML_SIDECAR')
$mlOriginalEnforce = [Environment]::GetEnvironmentVariable('AXION_ML_SIDECAR_ENFORCE')

$steps += Invoke-Step -Name 'phase2_shell_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_phase2_shell_smoke.py'))
}
$phase2 = Read-JsonOrNull $phase2SummaryPath
$checks.phase2_shell_smoke = [ordered]@{
  ok = ($null -ne $phase2) -and ($phase2.failed -eq 0) -and ($phase2.route_failed -eq 0)
  evidence = $phase2SummaryPath
}

$steps += Invoke-Step -Name 'shell_surface_contract_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_shell_surface_contract_smoke.py'))
}
$shellSurface = Read-JsonOrNull $shellSurfaceSummaryPath
$checks.shell_surface_contract_smoke = [ordered]@{
  ok = ($null -ne $shellSurface) -and ($shellSurface.checks_failed -eq 0)
  evidence = $shellSurfaceSummaryPath
}

$steps += Invoke-Step -Name 'windows_tools_execution_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_windows_tools_execution_smoke.py'))
}
$windowsToolsExecution = Read-JsonOrNull $windowsToolsExecutionSummaryPath
$checks.windows_tools_execution_smoke = [ordered]@{
  ok = ($null -ne $windowsToolsExecution) -and ($windowsToolsExecution.checks_failed -eq 0)
  evidence = $windowsToolsExecutionSummaryPath
}

$steps += Invoke-Step -Name 'parallel_cubed_mode_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_parallel_cubed_mode_smoke.py'))
}
$parallelCubedMode = Read-JsonOrNull $parallelCubedModeSummaryPath
$checks.parallel_cubed_mode_smoke = [ordered]@{
  ok = ($null -ne $parallelCubedMode) -and ($parallelCubedMode.checks_failed -eq 0)
  evidence = $parallelCubedModeSummaryPath
}

$steps += Invoke-Step -Name 'firmware_os_handoff_enforcement' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\runtime\firmware_os_handoff_enforcement_flow.py'))
}
$firmwareOsHandoff = Read-JsonOrNull $firmwareOsHandoffSummaryPath
$checks.firmware_os_handoff_enforcement = [ordered]@{
  ok = ($null -ne $firmwareOsHandoff) -and ($firmwareOsHandoff.status -eq 'PASS')
  evidence = $firmwareOsHandoffSummaryPath
}

$steps += Invoke-Step -Name 'master_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_master_smoke.py'))
}
$master = Read-JsonOrNull $masterSummaryPath
$checks.master_smoke = [ordered]@{
  ok = ($null -ne $master) -and ($master.checks_failed -eq 0)
  evidence = $masterSummaryPath
}

$steps += Invoke-Step -Name 'security_core_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_security_core_smoke.py'))
}
$security = Read-JsonOrNull $securitySummaryPath
$checks.security_core_smoke = [ordered]@{
  ok = ($null -ne $security) -and ($security.failed -eq 0)
  evidence = $securitySummaryPath
}

$steps += Invoke-Step -Name 'kernel_policy_contract_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_kernel_policy_contract_smoke.py'))
}
$kernelPolicy = Read-JsonOrNull $kernelPolicySummaryPath
$checks.kernel_policy_contract_smoke = [ordered]@{
  ok = ($null -ne $kernelPolicy) -and ($kernelPolicy.checks_failed -eq 0)
  evidence = $kernelPolicySummaryPath
}

$steps += Invoke-Step -Name 'kernel_subsystem_ownership_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_kernel_subsystem_ownership_smoke.py'))
}
$kernelSubsystem = Read-JsonOrNull $kernelSubsystemSummaryPath
$checks.kernel_subsystem_ownership_smoke = [ordered]@{
  ok = ($null -ne $kernelSubsystem) -and ($kernelSubsystem.checks_failed -eq 0)
  evidence = $kernelSubsystemSummaryPath
}

$steps += Invoke-Step -Name 'kernel_runtime_ownership_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_kernel_runtime_ownership_smoke.py'))
}
$kernelRuntime = Read-JsonOrNull $kernelRuntimeSummaryPath
$checks.kernel_runtime_ownership_smoke = [ordered]@{
  ok = ($null -ne $kernelRuntime) -and ($kernelRuntime.checks_failed -eq 0)
  evidence = $kernelRuntimeSummaryPath
}

$steps += Invoke-Step -Name 'kernel_execution_depth_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_kernel_execution_depth_smoke.py'))
}
$kernelExecutionDepth = Read-JsonOrNull $kernelExecutionDepthSummaryPath
$checks.kernel_execution_depth_smoke = [ordered]@{
  ok = ($null -ne $kernelExecutionDepth) -and ($kernelExecutionDepth.checks_failed -eq 0)
  evidence = $kernelExecutionDepthSummaryPath
}

$steps += Invoke-Step -Name 'compatibility_module_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_compatibility_module_smoke.py'))
}
$compatModule = Read-JsonOrNull $compatModuleSummaryPath
$checks.compatibility_module_smoke = [ordered]@{
  ok = ($null -ne $compatModule) -and ($compatModule.checks_failed -eq 0)
  evidence = $compatModuleSummaryPath
}

$steps += Invoke-Step -Name 'installer_replay_matrix_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_installer_replay_matrix_smoke.py'))
}
$installerReplay = Read-JsonOrNull $installerReplaySummaryPath
$checks.installer_replay_matrix_smoke = [ordered]@{
  ok = ($null -ne $installerReplay) -and ($installerReplay.failed -eq 0)
  evidence = $installerReplaySummaryPath
}

$steps += Invoke-Step -Name 'projection_session_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_projection_session_smoke.py'))
}
$projectionSession = Read-JsonOrNull $projectionSessionSummaryPath
$checks.projection_session_smoke = [ordered]@{
  ok = ($null -ne $projectionSession) -and ($projectionSession.checks_failed -eq 0)
  evidence = $projectionSessionSummaryPath
}

$steps += Invoke-Step -Name 'firewall_quarantine_adjudication_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_firewall_quarantine_adjudication_smoke.py'))
}
$fwq = Read-JsonOrNull $firewallQuarantineSummaryPath
$checks.firewall_quarantine_adjudication_smoke = [ordered]@{
  ok = ($null -ne $fwq) -and ($fwq.checks_failed -eq 0)
  evidence = $firewallQuarantineSummaryPath
}

$steps += Invoke-Step -Name 'operational_soak_recovery_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_operational_soak_recovery_smoke.py'))
}
$operationalSoak = Read-JsonOrNull $operationalSoakSummaryPath
$checks.operational_soak_recovery_smoke = [ordered]@{
  ok = ($null -ne $operationalSoak) -and ($operationalSoak.checks_failed -eq 0)
  evidence = $operationalSoakSummaryPath
}

$steps += Invoke-Step -Name 'media_engine_contract_smoke' -Action {
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_media_engine_contract_smoke.py'))
}
$mediaEngine = Read-JsonOrNull $mediaEngineSummaryPath
$checks.media_engine_contract_smoke = [ordered]@{
  ok = ($null -ne $mediaEngine) -and ($mediaEngine.checks_failed -eq 0)
  evidence = $mediaEngineSummaryPath
}

$steps += Invoke-Step -Name 'ml_security_sidecar' -Action {
  if($runMlSidecar){
    [Environment]::SetEnvironmentVariable('AXION_ENABLE_ML_SIDECAR','1')
  }
  if($EnforceMlSidecarAnomaly -or $RequireMlSidecar -or ($BuildProfile -eq 'release')){
    [Environment]::SetEnvironmentVariable('AXION_ML_SIDECAR_ENFORCE','1')
  }
  & $pythonInvocation.file_path @($pythonInvocation.args_prefix + (Join-Path $osRoot 'tools\qa\run_ml_security_sidecar.py'))
}
$mlSidecar = Read-JsonOrNull $mlSidecarSummaryPath
$mlOk = ($steps[-1].ok -eq $true)
if($null -ne $mlSidecar){
  if($mlSidecar.PSObject.Properties.Name -contains 'ok'){
    $mlOk = $mlOk -and [bool]$mlSidecar.ok
  }
  $mlStatus = [string]($mlSidecar.status)
  if($RequireMlSidecar -and $mlStatus -eq 'SKIPPED'){
    $mlOk = $false
  }
}
$checks.ml_security_sidecar = [ordered]@{
  ok = $mlOk
  evidence = $mlSidecarSummaryPath
}
[Environment]::SetEnvironmentVariable('AXION_ENABLE_ML_SIDECAR',$mlOriginalEnable)
[Environment]::SetEnvironmentVariable('AXION_ML_SIDECAR_ENFORCE',$mlOriginalEnforce)

$steps += Invoke-Step -Name 'firmware_gate' -Action {
  powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $osRoot 'tools\firmware\run_fw_gate.ps1')
}
$fw = Read-JsonOrNull $fwSummaryPath
$checks.firmware_gate = [ordered]@{
  ok = ($null -ne $fw) -and ($fw.overall -eq 'PASS')
  evidence = $fwSummaryPath
}

if(-not $SkipReproBuild){
  $steps += Invoke-Step -Name 'repro_build' -Action {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $osRoot 'tools\repro\build_once.ps1') -Version $Version -BuildProfile $BuildProfile
  }
  $checks.repro_build = [ordered]@{ ok = ($steps[-1].ok -eq $true); evidence = (Join-Path $osRoot ("out\release\{0}\manifest.json" -f $Version)) }
} else {
  $checks.repro_build = [ordered]@{ ok = $true; evidence = 'SKIPPED' }
}

if($runKernelLiveBoot){
  $steps += Invoke-Step -Name 'kernel_live_boot_wsl' -Action {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $osRoot 'tools\repro\verify_kernel_wsl.ps1') -Distro $KernelLiveBootDistro -TimeoutSec $KernelLiveBootTimeoutSec
  }
  $kernelVerifyLatest = Get-ChildItem -Path (Join-Path $osRoot 'out\repro') -Filter 'verify_kernel_wsl_*.json' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $kernelVerifyEvidence = if($kernelVerifyLatest){ $kernelVerifyLatest.FullName } else { (Join-Path $osRoot 'out\repro') }
  $checks.kernel_live_boot_wsl = [ordered]@{ ok = ($steps[-1].ok -eq $true); evidence = $kernelVerifyEvidence }
} else {
  $checks.kernel_live_boot_wsl = [ordered]@{ ok = $true; evidence = 'SKIPPED_NOT_REQUESTED' }
}

if($runUnifiedStackSmoke){
  $steps += Invoke-Step -Name 'unified_stack_smoke' -Action {
    if(-not (Test-Path $stackScriptPath)){
      throw ("Unified stack script not found: {0}" -f $stackScriptPath)
    }
    $tmpStamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
    $stdoutTmp = Join-Path $outDir ("unified_stack_smoke_{0}.stdout.tmp" -f $tmpStamp)
    $stderrTmp = Join-Path $outDir ("unified_stack_smoke_{0}.stderr.tmp" -f $tmpStamp)

    $proc = Start-Process -FilePath 'powershell.exe' `
      -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$stackScriptPath,'-SkipFirmwareBuild','-QemuTimeoutSeconds',"$UnifiedStackQemuTimeoutSec") `
      -Wait -PassThru -NoNewWindow `
      -RedirectStandardOutput $stdoutTmp `
      -RedirectStandardError $stderrTmp

    $stackLines = @()
    if(Test-Path $stdoutTmp){ $stackLines += Get-Content -Path $stdoutTmp -ErrorAction SilentlyContinue }
    if(Test-Path $stderrTmp){
      $stderrLines = Get-Content -Path $stderrTmp -ErrorAction SilentlyContinue
      if($stderrLines -and $stderrLines.Count -gt 0){
        if($stackLines.Count -gt 0){ $stackLines += '--- STDERR ---' }
        $stackLines += $stderrLines
      }
    }
    if(Test-Path $stdoutTmp){ Remove-Item -LiteralPath $stdoutTmp -Force -ErrorAction SilentlyContinue }
    if(Test-Path $stderrTmp){ Remove-Item -LiteralPath $stderrTmp -Force -ErrorAction SilentlyContinue }

    $stackText = @($stackLines | ForEach-Object { $_.ToString() }) -join "`n"
    $stackExit = $proc.ExitCode
    $timeoutBootOk = ($stackText -match 'Smoke run reached timeout after') -and ($stackText -match 'KERNEL_MAIN_START') -and ($stackText -match 'KDISK_LBA0_OK')
    if(($stackExit -ne 0) -and $timeoutBootOk){
      $global:LASTEXITCODE = 0
      Write-Output '[gate] unified_stack_smoke accepted timeout-verified boot success despite non-zero script exit.'
    } else {
      $global:LASTEXITCODE = $stackExit
    }
    $stackLines
  }
  $checks.unified_stack_smoke = [ordered]@{ ok = ($steps[-1].ok -eq $true); evidence = $stackScriptPath }
} else {
  $checks.unified_stack_smoke = [ordered]@{ ok = $true; evidence = 'SKIPPED_NOT_REQUESTED' }
}

if(-not $SkipQemuDryRun){
  $steps += Invoke-Step -Name 'qemu_boot_dryrun' -Action {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $osRoot 'tools\repro\boot_qemu_once.ps1') -Version $Version -DryRun
  }
  $checks.qemu_boot_dryrun = [ordered]@{ ok = ($steps[-1].ok -eq $true); evidence = (Join-Path $osRoot ("out\repro\qemu_boot_meta_{0}.json" -f $Version)) }
} else {
  $checks.qemu_boot_dryrun = [ordered]@{ ok = $true; evidence = 'SKIPPED' }
}

if(-not $SkipGoldenDryRun){
  $steps += Invoke-Step -Name 'golden_vm_smoke_dryrun' -Action {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $osRoot 'tools\qa\run_golden_vm_smoke.ps1') -Version $Version -DryRun
  }
  $golden = Read-JsonOrNull $goldenSummaryPath
  $goldenOk = ($null -ne $golden) -and (($golden.overall -eq 'SKIPPED') -or ($golden.overall -eq 'PASS'))
  $checks.golden_vm_smoke_dryrun = [ordered]@{ ok = $goldenOk; evidence = $goldenSummaryPath }
} else {
  $checks.golden_vm_smoke_dryrun = [ordered]@{ ok = $true; evidence = 'SKIPPED' }
}

$critical = @('phase2_shell_smoke','shell_surface_contract_smoke','windows_tools_execution_smoke','parallel_cubed_mode_smoke','firmware_os_handoff_enforcement','master_smoke','security_core_smoke','kernel_policy_contract_smoke','kernel_subsystem_ownership_smoke','kernel_runtime_ownership_smoke','kernel_execution_depth_smoke','compatibility_module_smoke','installer_replay_matrix_smoke','projection_session_smoke','firewall_quarantine_adjudication_smoke','operational_soak_recovery_smoke','media_engine_contract_smoke','firmware_gate','repro_build')
if($runKernelLiveBoot -or $RequireKernelLiveBoot){
  $critical += @('kernel_live_boot_wsl')
}
if($runUnifiedStackSmoke -or $RequireUnifiedStackSmoke){
  $critical += @('unified_stack_smoke')
}
if($runMlSidecar -or $RequireMlSidecar){
  $critical += @('ml_security_sidecar')
}
$criticalOk = $true
foreach($k in $critical){
  if((-not $checks.Contains($k)) -or (-not [bool]$checks[$k].ok)){
    $criticalOk = $false
    break
  }
}

$overallOk = $true
foreach($entry in $checks.GetEnumerator()){
  if(-not [bool]$entry.Value.ok){
    $overallOk = $false
    break
  }
}

$summary = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString('o')
  suite = 'axionos_release_gate'
  version = $Version
  build_profile = $BuildProfile
  os_root = $osRoot
  checks = $checks
  critical_ok = $criticalOk
  overall_ok = $overallOk
  steps = $steps
}

$summary | ConvertTo-Json -Depth 10 | Set-Content -Path $summaryPath -Encoding UTF8
Write-Output ("RELEASE_GATE_SUMMARY:{0}" -f $summaryPath)
Write-Output ("RELEASE_GATE_CRITICAL:{0}" -f $(if($criticalOk){'PASS'}else{'FAIL'}))
Write-Output ("RELEASE_GATE_OVERALL:{0}" -f $(if($overallOk){'PASS'}else{'FAIL'}))

if($overallOk){ exit 0 }
exit 1
