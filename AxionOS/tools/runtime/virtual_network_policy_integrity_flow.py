#!/usr/bin/env python3
from vm_policy_integrity_core import run_vm_policy_integrity


if __name__ == '__main__':
    run_vm_policy_integrity(
        contract_id='virtual_network_policy_integrity',
        fail1_code='VNET_POLICY_BYPASS_DETECTED',
        fail2_code='VNET_RULESET_DRIFT',
        exit_codes={
            'VNET_POLICY_BYPASS_DETECTED': 1903,
            'VNET_RULESET_DRIFT': 1904,
        },
        required_controls=['vnet.policy', 'vnet.egress', 'vnet.netns'],
    )
