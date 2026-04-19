#!/usr/bin/env python3
from vm_policy_integrity_core import run_vm_policy_integrity


if __name__ == '__main__':
    run_vm_policy_integrity(
        contract_id='vm_kernel_cmdline_lock_integrity',
        fail1_code='KERNEL_CMDLINE_MUTABLE',
        fail2_code='UNTRUSTED_BOOT_PARAMS_ACCEPTED',
        exit_codes={
            'KERNEL_CMDLINE_MUTABLE': 1915,
            'UNTRUSTED_BOOT_PARAMS_ACCEPTED': 1916,
        },
        required_controls=['kernel.cmdline_lock', 'kernel.boot_param_allowlist'],
    )
