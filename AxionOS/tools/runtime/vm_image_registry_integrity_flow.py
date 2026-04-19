#!/usr/bin/env python3
from vm_policy_integrity_core import run_vm_policy_integrity


if __name__ == '__main__':
    run_vm_policy_integrity(
        contract_id='vm_image_registry_integrity',
        fail1_code='VM_IMAGE_TAG_MUTABILITY_ALLOWED',
        fail2_code='VM_IMAGE_SOURCE_UNTRUSTED',
        exit_codes={
            'VM_IMAGE_TAG_MUTABILITY_ALLOWED': 1925,
            'VM_IMAGE_SOURCE_UNTRUSTED': 1926,
        },
        required_controls=['image.tag_immutability', 'image.trusted_source'],
    )
