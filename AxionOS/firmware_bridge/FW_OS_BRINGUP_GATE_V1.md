# Firmware-First Bringup Gate v1

Goal: block OS test cycles until firmware baseline passes deterministic gate checks.

## Gate order (must pass in sequence)
1. Firmware build pass (OVMF/target profile)
2. Firmware hash/signature capture
3. QEMU boot smoke pass
4. Device init contract checks
5. Boot handoff contract proof to AxionOS
6. Recovery path sanity (rollback media)

## Pass criteria
- `FW_BUILD_OK`
- `FW_BOOT_SMOKE_OK`
- `FW_HANDOFF_OK`
- `FW_RECOVERY_OK`

If any fail -> OS integration test is blocked.

## Artifacts
- `<AXIONOS_ROOT>\out\fw_gate\build.log`
- `<AXIONOS_ROOT>\out\fw_gate\boot.log`
- `<AXIONOS_ROOT>\out\fw_gate\handoff.json`
- `<AXIONOS_ROOT>\out\fw_gate\summary.json`

