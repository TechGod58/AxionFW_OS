#!/usr/bin/env python3
from vm_policy_integrity_core import run_vm_policy_integrity


if __name__ == '__main__':
    run_vm_policy_integrity(
        contract_id='vm_disk_encryption_integrity',
        fail1_code='VM_DISK_UNENCRYPTED_VOLUME_ALLOWED',
        fail2_code='VM_DISK_KEY_WRONG_TENANT',
        exit_codes={
            'VM_DISK_UNENCRYPTED_VOLUME_ALLOWED': 1907,
            'VM_DISK_KEY_WRONG_TENANT': 1908,
        },
        required_controls=['disk.encryption', 'disk.key_tenant'],
    )
