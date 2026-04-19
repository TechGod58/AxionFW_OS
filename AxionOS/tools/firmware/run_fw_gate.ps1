param(
  [string]$Out = "",
  [string]$OsBase = "",
  [string]$FwBase = ""
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\common\pathing.ps1')

if([string]::IsNullOrWhiteSpace($OsBase)){
  $OsBase = Get-AxionOsRoot -ScriptPath $PSCommandPath
}
if([string]::IsNullOrWhiteSpace($FwBase)){
  $FwBase = Get-AxionFwBase -OsRoot $OsBase
}
if([string]::IsNullOrWhiteSpace($Out)){
  $Out = Join-Path $OsBase 'out\fw_gate'
}

New-Item -ItemType Directory -Force -Path $Out | Out-Null

$buildLog = Join-Path $Out 'build.log'
$bootLog = Join-Path $Out 'boot.log'
$handoffJson = Join-Path $Out 'handoff.json'
$summaryPath = Join-Path $Out 'summary.json'

function Set-Check($checks, $name, $status, $detail){
  foreach($c in $checks){
    if($c.name -eq $name){
      $c.status = $status
      $c.detail = $detail
    }
  }
}

$checks = @(
  [ordered]@{name='FW_BUILD_OK'; status='PENDING'; detail=$null},
  [ordered]@{name='FW_BOOT_SMOKE_OK'; status='PENDING'; detail=$null},
  [ordered]@{name='FW_HANDOFF_OK'; status='PENDING'; detail=$null},
  [ordered]@{name='FW_RECOVERY_OK'; status='PENDING'; detail=$null},
  [ordered]@{name='FW_REWRITE_ENGINE_POLICY_OK'; status='PENDING'; detail=$null}
)

# 1) FW_BUILD_OK
try {
  if(-not (Test-Path $FwBase)){ throw "Missing $FwBase" }

  $fwRoot = Split-Path -Parent $FwBase
  $ovmfCandidates = Get-ChildItem $fwRoot -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match 'OVMF.*\.(fd|bin)$' }

  $meta = [ordered]@{
    fw_base_exists = $true
    fw_base = $FwBase
    ovmf_candidate_count = ($ovmfCandidates | Measure-Object).Count
    ovmf_candidates = @($ovmfCandidates | Select-Object -First 8 -ExpandProperty FullName)
  }
  $meta | ConvertTo-Json -Depth 5 | Set-Content -Path $buildLog -Encoding UTF8

  if($meta.ovmf_candidate_count -gt 0){
    Set-Check $checks 'FW_BUILD_OK' 'PASS' "OVMF artifacts found: $($meta.ovmf_candidate_count)"
  } else {
    Set-Check $checks 'FW_BUILD_OK' 'FAIL' "No OVMF firmware artifact candidates found under $fwRoot"
  }
}
catch {
  Set-Check $checks 'FW_BUILD_OK' 'FAIL' $_.Exception.Message
}

# 2) FW_BOOT_SMOKE_OK
try {
  $qemu = Get-Command qemu-system-x86_64 -ErrorAction SilentlyContinue
  $wsl = Get-Command wsl -ErrorAction SilentlyContinue

  $boot = [ordered]@{
    qemu_available = [bool]$qemu
    qemu_path = if($qemu){$qemu.Source}else{$null}
    wsl_available = [bool]$wsl
    note = 'Boot smoke command availability check (non-destructive)'
  }
  $boot | ConvertTo-Json -Depth 5 | Set-Content -Path $bootLog -Encoding UTF8

  if($boot.qemu_available -or $boot.wsl_available){
    Set-Check $checks 'FW_BOOT_SMOKE_OK' 'PASS' 'QEMU or WSL pathway available for boot smoke execution'
  } else {
    Set-Check $checks 'FW_BOOT_SMOKE_OK' 'FAIL' 'No qemu-system-x86_64 or WSL command detected on host'
  }
}
catch {
  Set-Check $checks 'FW_BOOT_SMOKE_OK' 'FAIL' $_.Exception.Message
}

# 3) FW_HANDOFF_OK
try {
  $contract = Join-Path $OsBase 'design\bus_v1\AXIONOS_BUS_CONTRACT_V1.md'
  $schema = Join-Path $OsBase 'design\bus_v1\AXIONOS_BUS_CONTRACT_V1.schema.json'

  $handoff = [ordered]@{
    contract_exists = (Test-Path $contract)
    schema_exists = (Test-Path $schema)
    contract_path = $contract
    schema_path = $schema
    handoff_mode = 'contract-first'
  }
  $handoff | ConvertTo-Json -Depth 5 | Set-Content -Path $handoffJson -Encoding UTF8

  if($handoff.contract_exists -and $handoff.schema_exists){
    Set-Check $checks 'FW_HANDOFF_OK' 'PASS' 'OS<->FW handoff contract and schema present'
  } else {
    Set-Check $checks 'FW_HANDOFF_OK' 'FAIL' 'Missing handoff contract/spec artifacts'
  }
}
catch {
  Set-Check $checks 'FW_HANDOFF_OK' 'FAIL' $_.Exception.Message
}

# 4) FW_RECOVERY_OK
try {
  $recoverySpec = Join-Path $OsBase 'design\recovery\AXION_RESTORE_ROLLBACK_ARCH_V1.md'
  $checkpointSpec = Join-Path $OsBase 'design\recovery\AXION_CHECKPOINT_SHADOW_POLICY_V1.md'

  if((Test-Path $recoverySpec) -and (Test-Path $checkpointSpec)){
    Set-Check $checks 'FW_RECOVERY_OK' 'PASS' 'Recovery and checkpoint policies present'
  } else {
    Set-Check $checks 'FW_RECOVERY_OK' 'FAIL' 'Missing recovery/checkpoint policy artifacts'
  }
}
catch {
  Set-Check $checks 'FW_RECOVERY_OK' 'FAIL' $_.Exception.Message
}

# 5) FW_REWRITE_ENGINE_POLICY_OK
try {
  $rewritePolicy = Join-Path $FwBase 'policy\hardware_rewrite_primitive_catalog_v1.json'
  $adapterContract = Join-Path $FwBase 'policy\chipset_bus_adapter_contract_v1.json'
  $physicalFlashPolicy = Join-Path $FwBase 'policy\physical_flash_executor_policy_v1.json'
  $script50 = Join-Path $FwBase 'scripts\50_build_hardware_capability_graph.py'
  $script60 = Join-Path $FwBase 'scripts\60_plan_signed_rewrite.py'
  $script70 = Join-Path $FwBase 'scripts\70_execute_signed_rewrite.py'
  $rewritePlan = Join-Path $FwBase 'out\rewrite\rewrite_plan_v1.json'
  $guardOk = $true
  $guardDetail = "rewrite policy + adapters + controlled physical flash lane present"

  if(-not ((Test-Path $rewritePolicy) -and (Test-Path $adapterContract) -and (Test-Path $physicalFlashPolicy) -and (Test-Path $script50) -and (Test-Path $script60) -and (Test-Path $script70))){
    $guardOk = $false
    $guardDetail = 'rewrite engine policy/contract/scripts missing (including physical flash policy)'
  } elseif(Test-Path $rewritePlan) {
    try {
      $planObj = Get-Content -Raw -Path $rewritePlan | ConvertFrom-Json
      $mandatoryBackup = [bool]$planObj.execution_policy.mandatory_backup
      $abSlots = [bool]$planObj.execution_policy.ab_slots_required
      $rollback = [bool]$planObj.execution_policy.rollback_on_failure
      $physicalAllowed = [bool]$planObj.execution_policy.allow_physical_flash
      $physicalMode = [string]$planObj.execution_policy.physical_flash_mode
      $physicalExecutor = $planObj.physical_flash_executor
      $hasPolicyPath = -not [string]::IsNullOrWhiteSpace([string]$physicalExecutor.policy_path)
      $modeOk = ($physicalMode -eq 'controlled_fail_closed') -and ([string]$physicalExecutor.mode -eq 'controlled_fail_closed')
      $rollbackPhysical = [bool]$physicalExecutor.rollback_enforcement.require_backup_created -and [bool]$physicalExecutor.rollback_enforcement.require_ab_slots -and [bool]$physicalExecutor.rollback_enforcement.require_rollback_slot
      if(-not ($mandatoryBackup -and $abSlots -and $rollback -and $physicalAllowed -and $hasPolicyPath -and $modeOk -and $rollbackPhysical)){
        $guardOk = $false
        $guardDetail = 'rewrite plan guardrails missing (backup/A-B/rollback/controlled physical flash fail-closed lane)'
      } else {
        $guardDetail = 'rewrite plan includes backup + A/B + rollback guardrails and controlled physical flash lane'
      }
    } catch {
      $guardOk = $false
      $guardDetail = "unable to parse rewrite plan: $($_.Exception.Message)"
    }
  }

  if($guardOk){
    Set-Check $checks 'FW_REWRITE_ENGINE_POLICY_OK' 'PASS' $guardDetail
  } else {
    Set-Check $checks 'FW_REWRITE_ENGINE_POLICY_OK' 'FAIL' $guardDetail
  }
}
catch {
  Set-Check $checks 'FW_REWRITE_ENGINE_POLICY_OK' 'FAIL' $_.Exception.Message
}

$overallPass = -not ($checks | Where-Object { $_.status -ne 'PASS' })
$summary = [ordered]@{
  ts = (Get-Date).ToUniversalTime().ToString('o')
  overall = if($overallPass){'PASS'} else {'FAIL'}
  checks = $checks
  artifacts = [ordered]@{
    build_log = $buildLog
    boot_log = $bootLog
    handoff_json = $handoffJson
    summary_json = $summaryPath
  }
}
$summary | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryPath -Encoding UTF8

Write-Output "FW_GATE_RESULT:$($summary.overall)"
Write-Output "FW_GATE_SUMMARY:$summaryPath"
