param(
  [switch]$SelfCheck
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$validator = Join-Path $repo 'tools\contracts\validate_registry.py'
$out = Join-Path $repo 'out\contracts\registry_validation.json'
$publish = Join-Path $repo 'ci\publish_contract_artifacts.ps1'
$assertSvc = Join-Path $repo 'tools\contracts\assert_services_negative_codes.py'
$assertTm = Join-Path $repo 'tools\contracts\assert_task_manager_negative_codes.py'
$gateCfg = Join-Path $repo 'config\release_critical_gates.json'
$emitInventory = Join-Path $repo 'tools\governance\emit_release_gate_inventory.py'
$gates = @(

  @{id='observability_unified_gate'; exit=501},

  @{id='configuration_immutable_field_policy'; exit=531},

  @{id='secrets_handling_integrity'; exit=551},

  @{id='artifact_provenance_integrity'; exit=571},

  @{id='runtime_isolation_integrity'; exit=591},

  @{id='dependency_version_lock_integrity'; exit=611},

  @{id='build_reproducibility_integrity'; exit=631},

  @{id='backup_restore_integrity'; exit=651},

  @{id='time_sync_integrity'; exit=671},

  @{id='identity_access_integrity'; exit=691},

  @{id='network_trust_boundary_integrity'; exit=711},

  @{id='audit_log_immutability_integrity'; exit=751},

  @{id='state_machine_transition_integrity'; exit=771},

  @{id='privilege_boundary_integrity'; exit=791},

  @{id='cluster_membership_integrity'; exit=911},

  @{id='service_discovery_integrity'; exit=931},

  @{id='scheduler_decision_determinism_integrity'; exit=951},

  @{id='storage_snapshot_integrity'; exit=971},

  @{id='leader_election_integrity'; exit=991},

  @{id='inter_service_mtls_identity_integrity'; exit=1011},

  @{id='consensus_log_integrity'; exit=1031},

  @{id='admission_control_integrity'; exit=1051},

  @{id='configuration_rollout_consistency_integrity'; exit=1071},

  @{id='workload_identity_attestation_integrity'; exit=1091},

  @{id='runtime_api_contract_integrity'; exit=1111},

  @{id='event_bus_delivery_integrity'; exit=1131},

  @{id='state_checkpoint_consistency_integrity'; exit=1151},

  @{id='distributed_rate_limit_integrity'; exit=1211},

  @{id='secrets_rotation_consistency_integrity'; exit=1221},

  @{id='control_plane_reconciliation_integrity'; exit=1231},

  @{id='artifact_supply_chain_integrity'; exit=1241},

  @{id='policy_compiler_integrity'; exit=1261},

  @{id='idempotency_semantics_integrity'; exit=1281},

  @{id='transactional_outbox_integrity'; exit=1301},

  @{id='schema_migration_integrity'; exit=1321},

  @{id='dead_letter_queue_integrity'; exit=1341},

  @{id='retry_backoff_integrity'; exit=1441},

  @{id='poison_message_quarantine_integrity'; exit=1451},

  @{id='consumer_offset_commit_integrity'; exit=1461},

  @{id='exactly_once_delivery_integrity'; exit=1481},

  @{id='saga_compensation_integrity'; exit=1531},

  @{id='inbox_outbox_pairing_integrity'; exit=1541},

  @{id='event_schema_compatibility_integrity'; exit=1611},

  @{id='boss_button_integrity'; exit=1663},

  @{id='parallel_cubed_sandbox_domain_integrity'; exit=1664},

  @{id='event_schema_integrity'; exit=2001},

  @{id='producer_sequence_integrity'; exit=2011},

  @{id='consumer_group_balance_integrity'; exit=2021},

  @{id='hotkey_layout_integrity'; exit=2031},

  @{id='hotkey_action_registry_integrity'; exit=2041},

  @{id='message_deduplication_store_integrity'; exit=2051},

  @{id='vm_test_harness_integrity'; exit=2061},

  @{id='vm_image_build_provenance_integrity'; exit=2071},

  @{id='usb_device_isolation_integrity'; exit=2081},

  @{id='thunderbolt_dma_policy_integrity'; exit=2091},

  @{id='pcie_hotplug_isolation_integrity'; exit=2101},

  @{id='backpressure_enforcement_integrity'; exit=2102},

  @{id='peripheral_firmware_trust_integrity'; exit=2111},

  @{id='checkpoint_lineage_integrity'; exit=2112},

  @{id='external_storage_execution_policy_integrity'; exit=2121},

  @{id='consumer_rebalance_state_safety_integrity'; exit=2122},

  @{id='peripheral_interrupt_isolation_integrity'; exit=2131},

  @{id='dead_letter_routing_consistency_integrity'; exit=2132},

  @{id='spi_peripheral_access_policy_integrity'; exit=2141},

  @{id='dedup_window_alignment_integrity'; exit=2142},

  @{id='i2c_bus_trust_policy_integrity'; exit=2151},

  @{id='event_time_ordering_integrity'; exit=2152},

  @{id='uart_console_exposure_integrity'; exit=2161},

  @{id='event_time_watermark_alignment_integrity'; exit=2162},

  @{id='embedded_controller_trust_integrity'; exit=2171},

  @{id='exactly_once_state_update_integrity'; exit=2172},

  @{id='sensor_bus_isolation_integrity'; exit=2181},

  @{id='late_event_handling_integrity'; exit=2182},

  @{id='mmio_window_policy_integrity'; exit=2191},

  @{id='offset_to_state_atomicity_integrity'; exit=2192},

  @{id='interconnect_link_training_integrity'; exit=2201},

  @{id='poison_event_quarantine_integrity'; exit=2202},

  @{id='fabric_error_containment_integrity'; exit=2211},

  @{id='producer_epoch_fencing_integrity'; exit=2212},

  @{id='cross_socket_trust_integrity'; exit=2221},

  @{id='restore_replay_determinism_integrity'; exit=2222},

  @{id='fabric_bandwidth_partition_integrity'; exit=2231},

  @{id='retry_policy_coupling_integrity'; exit=2232},

  @{id='interconnect_firmware_consistency_integrity'; exit=2241},

  @{id='state_schema_evolution_integrity'; exit=2242},

  @{id='pcie_fabric_policy_integrity'; exit=2251},

  @{id='state_store_checkpoint_integrity'; exit=2252},

  @{id='clock_source_integrity'; exit=2261},

  @{id='state_store_compaction_integrity'; exit=2262},

  @{id='pll_configuration_integrity'; exit=2271},

  @{id='state_store_corruption_detection_integrity'; exit=2272},

  @{id='power_state_transition_integrity'; exit=2281},

  @{id='state_store_ttl_integrity'; exit=2282},

  @{id='frequency_scaling_policy_integrity'; exit=2291},

  @{id='stream_correctness_telemetry_integrity'; exit=2292},

  @{id='virtual_network_policy_integrity'; exit=2301},

  @{id='stream_partition_affinity_integrity'; exit=2302},

  @{id='vm_snapshot_restore_isolation_integrity'; exit=2311},

  @{id='stream_retention_window_integrity'; exit=2312},

  @{id='vm_disk_encryption_integrity'; exit=2321},

  @{id='time_window_boundary_integrity'; exit=2322},

  @{id='vm_memory_scrub_integrity'; exit=2331},

  @{id='watermark_progress_integrity'; exit=2332},

  @{id='vm_device_passthrough_integrity'; exit=2341},

  @{id='window_aggregation_consistency_integrity'; exit=2342},

  @{id='vm_kernel_cmdline_lock_integrity'; exit=2351},

  @{id='vm_guest_tools_channel_integrity'; exit=2361},

  @{id='vm_time_sync_tamper_integrity'; exit=2371},

  @{id='vm_entropy_source_integrity'; exit=2381},

  @{id='vm_image_registry_integrity'; exit=2391},

  @{id='vm_attestation_quote_integrity'; exit=2401},

  @{id='vm_console_channel_integrity'; exit=2411},

  @{id='voltage_rail_policy_integrity'; exit=2421},

  @{id='watchdog_timer_policy_integrity'; exit=2431},

  @{id='firmware_rollback_protection_integrity'; exit=2501},

  @{id='trusted_boot_measurement_chain_integrity'; exit=2521},

  @{id='platform_measured_boot_policy_integrity'; exit=2531},

  @{id='firmware_attestation_chain_integrity'; exit=2541},

  @{id='bootloader_key_rotation_integrity'; exit=2551},

  @{id='uefi_variable_policy_integrity'; exit=2561},

  @{id='spi_flash_descriptor_lock_integrity'; exit=2671},

  @{id='boot_guard_policy_fuse_integrity'; exit=2681},

  @{id='boot_guard_acm_verification_integrity'; exit=2691},

  @{id='tpm_event_log_integrity'; exit=2701},

  @{id='pcr_policy_binding_integrity'; exit=2711},

  @{id='firmware_image_layout_integrity'; exit=2721},

  @{id='microcode_patch_authenticity_integrity'; exit=2731},

  @{id='platform_fuse_configuration_integrity'; exit=2741},

  @{id='smm_handler_integrity'; exit=2751},

  @{id='dma_remapping_policy_integrity'; exit=2761},

  @{id='iommu_enforcement_integrity'; exit=2771},

  @{id='runtime_services_table_integrity'; exit=2781},

  @{id='option_rom_execution_policy_integrity'; exit=2791},

  @{id='chipset_lock_register_integrity'; exit=2801},

  @{id='secure_time_source_integrity'; exit=2811},

  @{id='runtime_measurement_anchor_integrity'; exit=2821},

  @{id='platform_identity_binding_integrity'; exit=2831},

  @{id='trusted_resume_path_integrity'; exit=2841},

  @{id='crashdump_protection_integrity'; exit=2851},

  @{id='debug_unlock_policy_integrity'; exit=2861},

  @{id='resume_memory_integrity'; exit=2871},

  @{id='post_boot_attestation_refresh_integrity'; exit=2881},

  @{id='sealed_storage_binding_integrity'; exit=2891},

  @{id='platform_event_forwarding_integrity'; exit=2901},

  @{id='recovery_mode_policy_integrity'; exit=2911},

  @{id='maintenance_override_integrity'; exit=2921},

  @{id='device_identity_attestation_integrity'; exit=2931},

  @{id='platform_certificate_rotation_integrity'; exit=2941},

  @{id='device_binding_anchor_integrity'; exit=2951},

  @{id='peripheral_trust_policy_integrity'; exit=2961},

  @{id='external_device_measurement_integrity'; exit=2971},

  @{id='device_trust_revocation_integrity'; exit=2981},

  @{id='device_runtime_access_policy_integrity'; exit=2991},

  @{id='hotplug_device_trust_integrity'; exit=2992},

  @{id='device_driver_runtime_policy_integrity'; exit=2993},

  @{id='device_dma_runtime_guard_integrity'; exit=2994},

  @{id='device_session_trust_integrity'; exit=2995},

  @{id='device_runtime_revocation_integrity'; exit=2996},

  @{id='reset_path_integrity'; exit=3291},

  @{id='failsafe_boot_path_integrity'; exit=3301},

  @{id='recovery_chain_integrity'; exit=3311},

  @{id='rollback_failsafe_integrity'; exit=3321},

  @{id='panic_response_policy_integrity'; exit=3331},

  @{id='platform_safe_mode_integrity'; exit=3341}

)



if($SelfCheck){
  $ids = @($gates | ForEach-Object { $_.id })
  $exits = @($gates | ForEach-Object { [int]$_.exit })
  $dupIds = $ids | Group-Object | Where-Object { $_.Count -gt 1 }
  $dupExits = $exits | Group-Object | Where-Object { $_.Count -gt 1 }
  $cfg = Get-Content $gateCfg -Raw | ConvertFrom-Json
  $cfgIds = @($cfg.gates | ForEach-Object { $_.contract_id })
  $missingFromScript = @($cfgIds | Where-Object { $ids -notcontains $_ })
  if($dupIds.Count -gt 0 -or $dupExits.Count -gt 0 -or $missingFromScript.Count -gt 0){
    Write-Output "SELF_CHECK_FAIL dup_ids=$($dupIds.Count) dup_exits=$($dupExits.Count) missing_from_script=$($missingFromScript -join ',')"
    exit 2
  }
  Write-Output 'SELF_CHECK_PASS'
  exit 0
}

Push-Location $repo
try {
  Write-Output "[contracts-gate] running: python $validator"
  python $validator
  $ec = $LASTEXITCODE
  Write-Output "[contracts-gate] validator_exit=$ec"
  if($ec -ne 0){ Write-Output "[contracts-gate] FAIL_FAST validator"; exit $ec }
  if(-not (Test-Path $out)){ Write-Output "[contracts-gate] FAIL_FAST missing artifact: $out"; exit 99 }

  $svcMode='start_denied'
  python .\tools\runtime\services_flow.py $svcMode > $null
  $svcEc=$LASTEXITCODE
  powershell -ExecutionPolicy Bypass -File .\ci\emit_contract_report.ps1 > $null
  $svcReport = Get-ChildItem .\out\contracts -Filter 'contract_report_*.json' -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  python $assertSvc --mode $svcMode --exit-code $svcEc --report $svcReport.FullName
  $saec=$LASTEXITCODE
  Write-Output "[contracts-gate] services_assert_exit=$saec"
  if($saec -ne 0){ Write-Output "[contracts-gate] FAIL_FAST services-code assertion"; exit $saec }

  $tmMode='kill_denied'
  python .\tools\runtime\task_manager_flow.py $tmMode > $null
  $tmEc=$LASTEXITCODE
  powershell -ExecutionPolicy Bypass -File .\ci\emit_contract_report.ps1 > $null
  $tmReport = Get-ChildItem .\out\contracts -Filter 'contract_report_*.json' -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  python $assertTm --mode $tmMode --exit-code $tmEc --report $tmReport.FullName
  $taec=$LASTEXITCODE
  Write-Output "[contracts-gate] task_manager_assert_exit=$taec"
  if($taec -ne 0){ Write-Output "[contracts-gate] FAIL_FAST task-manager assertion"; exit $taec }

  $latestReport = Get-ChildItem .\out\contracts -Filter 'contract_report_*.json' -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if(-not $latestReport){ Write-Output "[contracts-gate] FAIL_FAST missing contract report"; exit 99 }
  $reportObj = Get-Content $latestReport.FullName -Raw | ConvertFrom-Json

  foreach($g in $gates){
    $id=[string]$g.id
    $ex=[int]$g.exit
    $status=$null
    if($reportObj.PSObject.Properties.Name -contains $id){
      $sec = $reportObj.$id
      if($null -ne $sec){ $status=[string]$sec.status }
    } else {
      Write-Output "[contracts-gate] MISSING_SECTION $id"
    }
    Write-Output "[contracts-gate] $id=$status"
    if($status -ne 'PASS'){
      Write-Output "[contracts-gate] FAIL_FAST $id"
      exit $ex
    }
  }

  Write-Output "[contracts-gate] PASS artifact=$out"
}
finally {
  powershell -ExecutionPolicy Bypass -File $publish | ForEach-Object { Write-Output $_ }
  python $emitInventory | ForEach-Object { Write-Output $_ }
  Pop-Location
}





















