#!/usr/bin/env python3
from vm_policy_integrity_core import run_vm_policy_integrity


if __name__ == '__main__':
    run_vm_policy_integrity(
        contract_id='vm_snapshot_restore_isolation_integrity',
        fail1_code='VM_SNAPSHOT_RESTORE_CROSS_TENANT',
        fail2_code='VM_SNAPSHOT_METADATA_TAMPER',
        exit_codes={
            'VM_SNAPSHOT_RESTORE_CROSS_TENANT': 1905,
            'VM_SNAPSHOT_METADATA_TAMPER': 1906,
        },
        required_controls=['snapshot.tenant_isolation', 'snapshot.metadata_integrity'],
    )
