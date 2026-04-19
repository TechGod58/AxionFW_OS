#!/usr/bin/env python3
from vm_policy_integrity_core import run_vm_policy_integrity


if __name__ == '__main__':
    run_vm_policy_integrity(
        contract_id='vm_console_channel_integrity',
        fail1_code='VM_CONSOLE_UNAUTH_ACCESS',
        fail2_code='VM_CONSOLE_SESSION_HIJACK',
        exit_codes={
            'VM_CONSOLE_UNAUTH_ACCESS': 1929,
            'VM_CONSOLE_SESSION_HIJACK': 1930,
        },
        required_controls=['console.authz', 'console.session'],
    )
