#!/usr/bin/env python3
from vm_policy_integrity_core import run_vm_policy_integrity


if __name__ == '__main__':
    run_vm_policy_integrity(
        contract_id='vm_memory_scrub_integrity',
        fail1_code='VM_MEMORY_SCRUB_SKIPPED',
        fail2_code='VM_MEMORY_REUSE_DETECTED',
        exit_codes={
            'VM_MEMORY_SCRUB_SKIPPED': 1909,
            'VM_MEMORY_REUSE_DETECTED': 1910,
        },
        required_controls=['memory.scrub_on_alloc', 'memory.no_plain_reuse'],
    )
