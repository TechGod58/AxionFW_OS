#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
import argparse, json, os, glob
from datetime import datetime, timezone
from hashlib import sha256

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path

ROOT = str(axion_path())

def now_iso(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def read_json(path):
    if not os.path.exists(path): return None
    with open(path,'r',encoding='utf-8-sig') as f: return json.load(f)
def sha(path):
    if not os.path.exists(path): return None
    h=sha256()
    with open(path,'rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()
def ensure_list(v):
    if v is None: return []
    return v if isinstance(v,list) else [v]
def latest(root,name):
    cand=glob.glob(os.path.join(root,'**',name), recursive=True)
    if not cand: return None
    cand.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return cand[0]
def sec(name):
    audit=os.path.join(ROOT,'out','runtime',f'{name}_audit.json')
    smoke=os.path.join(ROOT,'out','runtime',f'{name}_smoke.json')
    s=read_json(smoke)
    if s is not None or os.path.exists(audit):
        return {'status':(s or {}).get('status','UNKNOWN'),'audit_path':audit,'smoke_path':smoke,'failures':ensure_list((s or {}).get('failures'))}
    return None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--build-id', required=False); args=ap.parse_args()
    build_id=args.build_id or ('AXION_BUILD_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    idx_path=os.path.join(ROOT,'contracts','registry','index.json')
    reg_path=os.path.join(ROOT,'out','contracts','registry_validation.json')
    idx=read_json(idx_path) or {}
    reg=read_json(reg_path) or {}
    entries=[]
    for e in idx.get('entries',[]):
        rel=e.get('path','')
        abs_path=os.path.normpath(os.path.join(ROOT, rel.replace('/','\\')))
        entries.append({'contract_id':e.get('contract_id'),'category':e.get('category'),'version':e.get('version'),'path':rel,'abs_path':abs_path,'sha256':e.get('sha256'),'sha256_actual':sha(abs_path),'exists':os.path.exists(abs_path)})
    entries=sorted(entries,key=lambda x:(str(x.get('contract_id')),str(x.get('version'))))
    qa_root=os.path.join(ROOT,'out','qa_bundle'); gates=[]
    sm=latest(qa_root,'smoke.json'); ng=latest(qa_root,'negative_test.json')
    if sm: gates.append({'gate':'smoke','status':'UNKNOWN','evidence':sm})
    if ng: gates.append({'gate':'negative_tests','status':'UNKNOWN','evidence':ng})
    fw=reg.get('fw_handoff')
    if isinstance(fw,dict): fw=dict(fw); fw['failures']=ensure_list(fw.get('failures'))
    report={
      'build_id':build_id,'timestamp_utc':now_iso(),'repo_root':ROOT,
      'git':{'github_run_id':os.environ.get('GITHUB_RUN_ID'),'github_sha':os.environ.get('GITHUB_SHA'),'github_ref':os.environ.get('GITHUB_REF')},
      'registry':{'status':reg.get('validation_status','UNKNOWN'),'validation_path':reg_path,'failures':ensure_list(reg.get('failures')),'index_path':idx_path,'entry_count':len(entries),'entries':entries},
      'gates':gates,'fw_handoff':fw,
      'users_profiles':sec('users_profiles'),'services':sec('services'),'task_manager':sec('task_manager'),'accounts':sec('accounts'),'network':sec('network'),'apps':sec('apps'),
      'services_panel':sec('services_panel'),'devices_panel':sec('devices_panel'),'storage_panel':sec('storage_panel'),'security_panel':sec('security_panel'),'privacy_panel':sec('privacy_panel'),'updates_panel':sec('updates_panel'),'accessibility_panel':sec('accessibility_panel'),'display_panel':sec('display_panel'),'audio_panel':sec('audio_panel'),
      'permissions_panel':sec('permissions_panel'),'system_info_panel':sec('system_info_panel'),'power_energy_panel':sec('power_energy_panel'),'backup_restore_panel':sec('backup_restore_panel'),'logs_diagnostics_panel':sec('logs_diagnostics_panel'),'developer_tools_panel':sec('developer_tools_panel'),'policy_enforcement':sec('policy_enforcement'),
      'policy_hook_control_panel':sec('policy_hook_control_panel'),'policy_hook_service_operations':sec('policy_hook_service_operations'),'policy_hook_developer_tools':sec('policy_hook_developer_tools'),'policy_hook_backup_restore':sec('policy_hook_backup_restore'),
      'state_sync':sec('state_sync'),'state_sync_panel_write':sec('state_sync_panel_write'),'state_sync_service_state':sec('state_sync_service_state'),'state_sync_permissions_state':sec('state_sync_permissions_state'),'state_sync_backup_restore_state':sec('state_sync_backup_restore_state'),'state_sync_network_state':sec('state_sync_network_state'),'state_sync_accounts_state':sec('state_sync_accounts_state'),
      'ui_panel_action_dispatch':sec('ui_panel_action_dispatch'),'ui_panel_state_reflection':sec('ui_panel_state_reflection'),'ui_permission_gating':sec('ui_permission_gating'),'ui_action_ack':sec('ui_action_ack'),'ui_e2e_scenarios':sec('ui_e2e_scenarios'),'ui_e2e_retry_semantics':sec('ui_e2e_retry_semantics'),'ui_e2e_rollback_path':sec('ui_e2e_rollback_path'),'ui_e2e_multi_panel_concurrency':sec('ui_e2e_multi_panel_concurrency'),'telemetry_event_integrity':sec('telemetry_event_integrity'),'observability_hash_correlation':sec('observability_hash_correlation'),'observability_timestamp_integrity':sec('observability_timestamp_integrity'),'observability_anomaly_detection':sec('observability_anomaly_detection'),'observability_unified_gate':sec('observability_unified_gate'),'configuration_drift_detection':sec('configuration_drift_detection'),'configuration_immutable_field_policy':sec('configuration_immutable_field_policy'),'secrets_handling_integrity':sec('secrets_handling_integrity'),'artifact_provenance_integrity':sec('artifact_provenance_integrity'),'runtime_isolation_integrity':sec('runtime_isolation_integrity'),'dependency_version_lock_integrity':sec('dependency_version_lock_integrity'),'build_reproducibility_integrity':sec('build_reproducibility_integrity'),'backup_restore_integrity':sec('backup_restore_integrity'),'time_sync_integrity':sec('time_sync_integrity'),'identity_access_integrity':sec('identity_access_integrity'),'network_trust_boundary_integrity':sec('network_trust_boundary_integrity'),'crypto_key_lifecycle_integrity':sec('crypto_key_lifecycle_integrity'),'policy_evaluation_determinism_integrity':sec('policy_evaluation_determinism_integrity'),'audit_log_immutability_integrity':sec('audit_log_immutability_integrity'),'state_machine_transition_integrity':sec('state_machine_transition_integrity'),'privilege_boundary_integrity':sec('privilege_boundary_integrity'),'cross_service_trust_delegation_integrity':sec('cross_service_trust_delegation_integrity'),'data_lineage_integrity':sec('data_lineage_integrity'),'resource_quota_enforcement_integrity':sec('resource_quota_enforcement_integrity'),'update_rollout_integrity':sec('update_rollout_integrity'),'configuration_rollout_consistency_integrity':sec('configuration_rollout_consistency_integrity'),'workload_identity_attestation_integrity':sec('workload_identity_attestation_integrity'),'runtime_api_contract_integrity':sec('runtime_api_contract_integrity'),'event_bus_delivery_integrity':sec('event_bus_delivery_integrity'),'state_checkpoint_consistency_integrity':sec('state_checkpoint_consistency_integrity'),'distributed_rate_limit_integrity':sec('distributed_rate_limit_integrity'),'secrets_rotation_consistency_integrity':sec('secrets_rotation_consistency_integrity'),'control_plane_reconciliation_integrity':sec('control_plane_reconciliation_integrity'),'artifact_supply_chain_integrity':sec('artifact_supply_chain_integrity'),'policy_compiler_integrity':sec('policy_compiler_integrity'),'idempotency_semantics_integrity':sec('idempotency_semantics_integrity'),'transactional_outbox_integrity':sec('transactional_outbox_integrity'),'schema_migration_integrity':sec('schema_migration_integrity'),'dead_letter_queue_integrity':sec('dead_letter_queue_integrity'),'hotkey_action_registry_integrity':sec('hotkey_action_registry_integrity'),'hotkey_layout_integrity':sec('hotkey_layout_integrity'),'boss_button_integrity':sec('boss_button_integrity'),'parallel_cubed_sandbox_domain_integrity':sec('parallel_cubed_sandbox_domain_integrity'),'consumer_group_balance_integrity':sec('consumer_group_balance_integrity'),'producer_sequence_integrity':sec('producer_sequence_integrity'),'event_schema_compatibility_integrity':sec('event_schema_compatibility_integrity'),'event_schema_integrity':sec('event_schema_integrity'),'dispatch_fairness_integrity':sec('dispatch_fairness_integrity'),'priority_inversion_integrity':sec('priority_inversion_integrity'),'consumer_lag_reporting_integrity':sec('consumer_lag_reporting_integrity'),'inbox_outbox_pairing_integrity':sec('inbox_outbox_pairing_integrity'),'saga_compensation_integrity':sec('saga_compensation_integrity'),'message_deduplication_store_integrity':sec('message_deduplication_store_integrity'),'exactly_once_delivery_integrity':sec('exactly_once_delivery_integrity'),'replay_protection_integrity':sec('replay_protection_integrity'),'message_dedup_store_integrity':sec('message_dedup_store_integrity'),'exactly_once_effective_delivery_integrity':sec('exactly_once_effective_delivery_integrity'),'consumer_offset_commit_integrity':sec('consumer_offset_commit_integrity'),'poison_message_quarantine_integrity':sec('poison_message_quarantine_integrity'),'retry_backoff_integrity':sec('retry_backoff_integrity'),'cluster_membership_integrity':sec('cluster_membership_integrity'),'service_discovery_integrity':sec('service_discovery_integrity'),'scheduler_decision_determinism_integrity':sec('scheduler_decision_determinism_integrity'),'storage_snapshot_integrity':sec('storage_snapshot_integrity'),'leader_election_integrity':sec('leader_election_integrity'),'inter_service_mtls_identity_integrity':sec('inter_service_mtls_identity_integrity'),'consensus_log_integrity':sec('consensus_log_integrity'),'admission_control_integrity':sec('admission_control_integrity'),'stream_correctness_telemetry_integrity':sec('stream_correctness_telemetry_integrity'),'dedup_window_alignment_integrity':sec('dedup_window_alignment_integrity'),'poison_event_quarantine_integrity':sec('poison_event_quarantine_integrity'),'retry_policy_coupling_integrity':sec('retry_policy_coupling_integrity'),'dead_letter_routing_consistency_integrity':sec('dead_letter_routing_consistency_integrity'),'backpressure_enforcement_integrity':sec('backpressure_enforcement_integrity'),'consumer_rebalance_state_safety_integrity':sec('consumer_rebalance_state_safety_integrity'),'producer_epoch_fencing_integrity':sec('producer_epoch_fencing_integrity'),'offset_to_state_atomicity_integrity':sec('offset_to_state_atomicity_integrity'),'exactly_once_state_update_integrity':sec('exactly_once_state_update_integrity'),'restore_replay_determinism_integrity':sec('restore_replay_determinism_integrity'),'checkpoint_lineage_integrity':sec('checkpoint_lineage_integrity'),'state_store_corruption_detection_integrity':sec('state_store_corruption_detection_integrity'),'state_schema_evolution_integrity':sec('state_schema_evolution_integrity'),'state_store_ttl_integrity':sec('state_store_ttl_integrity'),'state_store_compaction_integrity':sec('state_store_compaction_integrity'),'time_window_boundary_integrity':sec('time_window_boundary_integrity'),'event_time_watermark_alignment_integrity':sec('event_time_watermark_alignment_integrity'),'stream_retention_window_integrity':sec('stream_retention_window_integrity'),'stream_partition_affinity_integrity':sec('stream_partition_affinity_integrity'),'state_store_checkpoint_integrity':sec('state_store_checkpoint_integrity'),'window_aggregation_consistency_integrity':sec('window_aggregation_consistency_integrity'),'late_event_handling_integrity':sec('late_event_handling_integrity'),'watermark_progress_integrity':sec('watermark_progress_integrity'),'event_time_ordering_integrity':sec('event_time_ordering_integrity'),'stream_retention_enforcement_integrity':sec('stream_retention_enforcement_integrity'),'producer_idempotence_window_integrity':sec('producer_idempotence_window_integrity'),'message_ordering_consistency_integrity':sec('message_ordering_consistency_integrity'),'event_time_windowing_integrity':sec('event_time_windowing_integrity'),'vm_test_harness_integrity':sec('vm_test_harness_integrity'),'vm_image_build_provenance_integrity':sec('vm_image_build_provenance_integrity'),'hypervisor_interface_integrity':sec('hypervisor_interface_integrity'),'secure_boot_chain_integrity':sec('secure_boot_chain_integrity'),'firmware_rollback_protection_integrity':sec('firmware_rollback_protection_integrity'),'firmware_attestation_chain_integrity':sec('firmware_attestation_chain_integrity'),'firmware_key_manifest_consistency_integrity':sec('firmware_key_manifest_consistency_integrity'),'uefi_variable_policy_integrity':sec('uefi_variable_policy_integrity'),'trusted_boot_measurement_chain_integrity':sec('trusted_boot_measurement_chain_integrity'),'platform_measured_boot_policy_integrity':sec('platform_measured_boot_policy_integrity'),'virtual_network_policy_integrity':sec('virtual_network_policy_integrity'),'vm_snapshot_restore_isolation_integrity':sec('vm_snapshot_restore_isolation_integrity'),'vm_disk_encryption_integrity':sec('vm_disk_encryption_integrity'),'vm_memory_scrub_integrity':sec('vm_memory_scrub_integrity'),'vm_device_passthrough_integrity':sec('vm_device_passthrough_integrity'),'vm_kernel_cmdline_lock_integrity':sec('vm_kernel_cmdline_lock_integrity'),'vm_guest_tools_channel_integrity':sec('vm_guest_tools_channel_integrity'),'vm_time_sync_tamper_integrity':sec('vm_time_sync_tamper_integrity'),'vm_entropy_source_integrity':sec('vm_entropy_source_integrity'),'vm_image_registry_integrity':sec('vm_image_registry_integrity'),'vm_attestation_quote_integrity':sec('vm_attestation_quote_integrity'),'vm_console_channel_integrity':sec('vm_console_channel_integrity')
    }
    out_dir=os.path.join(ROOT,'out','contracts'); os.makedirs(out_dir,exist_ok=True)
    out_path=os.path.join(out_dir,f'contract_report_{build_id}.json')
    with open(out_path,'w',encoding='utf-8') as f: json.dump(report,f,indent=2); f.write('\n')
    print(out_path)
if __name__=='__main__': main()





































































