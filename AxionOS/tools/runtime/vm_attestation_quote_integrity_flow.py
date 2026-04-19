#!/usr/bin/env python3
from vm_policy_integrity_core import run_vm_policy_integrity


if __name__ == '__main__':
    run_vm_policy_integrity(
        contract_id='vm_attestation_quote_integrity',
        fail1_code='VM_ATTESTATION_QUOTE_INVALID',
        fail2_code='VM_ATTESTATION_POLICY_BYPASS',
        exit_codes={
            'VM_ATTESTATION_QUOTE_INVALID': 1927,
            'VM_ATTESTATION_POLICY_BYPASS': 1928,
        },
        required_controls=['attestation.quote', 'attestation.policy'],
    )
