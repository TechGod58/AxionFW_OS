#!/usr/bin/env python3
from vm_policy_integrity_core import run_vm_policy_integrity


if __name__ == '__main__':
    run_vm_policy_integrity(
        contract_id='vm_guest_tools_channel_integrity',
        fail1_code='GUEST_TOOLS_PRIV_ESC_PATH',
        fail2_code='GUEST_TOOLS_UNAUTH_COMMAND',
        exit_codes={
            'GUEST_TOOLS_PRIV_ESC_PATH': 1917,
            'GUEST_TOOLS_UNAUTH_COMMAND': 1918,
        },
        required_controls=['guest_tools.authz', 'guest_tools.command_gate'],
    )
