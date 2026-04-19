#!/usr/bin/env python3
from vm_policy_integrity_core import run_vm_policy_integrity


if __name__ == '__main__':
    run_vm_policy_integrity(
        contract_id='vm_device_passthrough_integrity',
        fail1_code='PASSTHROUGH_UNAUTHORIZED_DEVICE',
        fail2_code='PASSTHROUGH_IOMMU_BYPASS',
        exit_codes={
            'PASSTHROUGH_UNAUTHORIZED_DEVICE': 1913,
            'PASSTHROUGH_IOMMU_BYPASS': 1914,
        },
        required_controls=['passthrough.allowlist', 'passthrough.iommu'],
    )
