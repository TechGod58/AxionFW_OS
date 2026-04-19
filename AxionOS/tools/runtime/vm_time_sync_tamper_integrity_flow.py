#!/usr/bin/env python3
from vm_policy_integrity_core import run_vm_policy_integrity


if __name__ == '__main__':
    run_vm_policy_integrity(
        contract_id='vm_time_sync_tamper_integrity',
        fail1_code='VM_TIME_SKEW_POLICY_BYPASS',
        fail2_code='VM_TIME_SOURCE_UNVERIFIED',
        exit_codes={
            'VM_TIME_SKEW_POLICY_BYPASS': 1919,
            'VM_TIME_SOURCE_UNVERIFIED': 1920,
        },
        required_controls=['time.skew_guard', 'time.source_verification'],
    )
