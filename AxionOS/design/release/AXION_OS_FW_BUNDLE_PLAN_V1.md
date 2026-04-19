# AXION Unified Sale Bundle (OS + Firmware) v1

Goal: sell AxionOS + Axion firmware together as a single affordable package.

## Commercial model
- Bundle target price: **$100**
- Includes:
  - AxionOS installer
  - Axion firmware package (board-specific profiles)
  - recovery/diagnostic tools

## Distribution format
- Single bootable USB image with:
  - OS installer
  - firmware installer toolkit
  - board detection + compatibility checks
  - offline docs + restore tools

## Boot USB structure (proposal)

```text
/boot
/installer/os
/installer/firmware
/profiles/boards
/recovery
/docs
/manifests
/hashes
```

## Installation flow
1. Boot USB
2. Detect board/hardware profile
3. Validate compatibility matrix
4. Install firmware package (approved path only)
5. Install AxionOS
6. Post-install health check + handoff report

## Safety gates
- No autonomous destructive flashing without explicit confirmation
- Signed package verification for OS/firmware
- Rollback checkpoints before firmware/OS apply

## Update strategy
- Combined update packs available, but can apply OS-only or FW-only when needed
- staged ring deployment support

## Definition of done (v1)
- One USB can perform clean install for supported profile set
- Signed manifest + hash verification mandatory
- End-to-end install report generated

All subsystem integration and release gating follows CONTRACT_FIRST_DEVELOPMENT_LOOP_V1.

Task Manager planning follows TASK_MANAGER_PRODUCT_ROADMAP_V1 and CONTRACT_FIRST_DEVELOPMENT_LOOP_V1.
