# AxionFW Base (UEFI/EDK2 + QEMU/OVMF) - Windows bootstrap

This is a starter scaffold to build and run a UEFI firmware image in QEMU (OVMF) on Windows.

## What this gives you
- Bootstrap script to fetch edk2 and build OVMF
- Deterministic artifact copy from `Build/OvmfX64/<TARGET>_<TOOLCHAIN>/FV`
- Split-firmware QEMU boot with a disposable runtime vars copy
- Minimal UEFI app source scaffold at `Firmware\Apps\AxionBusBase`

## Run order (x64 VS Dev Prompt)
1. `cd /d C:\AxionFW_OS\AxionFW\Base`
2. `scripts\01_bootstrap_edk2_ovmf.bat`
3. `scripts\03_run_qemu_no_tpm.bat`
4. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\40_run_policy_pipeline.ps1`

## Useful build flags
Set these before running `01_bootstrap_edk2_ovmf.bat`.

- `AXIONFW_REUSE_IF_PRESENT=1`
  Reuse an existing `Build/OvmfX64/<TARGET>_<TOOLCHAIN>/FV` output instead of rebuilding.
- `AXIONFW_CLEAN_BUILD=1`
  Remove the target build directory before building.
- `AXIONFW_SYNC_SUBMODULES=1`
  Sync the edk2 submodules before building. Leave this off for a stable local workspace.
- `AXIONFW_BUILD_TIMEOUT_SECS=1800`
  Bound the WSL `build` invocation with a timeout in seconds. `0` disables the timeout.
- `AXIONFW_BUILD_TARGET=DEBUG`
  Select the OVMF build target.
- `AXIONFW_TOOLCHAIN=GCC5`
  Select the EDK2 toolchain tag.

Example:
```bat
set AXIONFW_NO_PAUSE=1
set AXIONFW_REUSE_IF_PRESENT=1
set AXIONFW_BUILD_TIMEOUT_SECS=900
call C:\AxionFW_OS\AxionFW\Base\scripts\01_bootstrap_edk2_ovmf.bat
```

## Notes
- `03_run_qemu_no_tpm.bat` now prefers `OVMF_CODE.fd` + `OVMF_VARS.fd` and writes runtime state to `OVMF_VARS.runtime.fd`.
- This is the correct first step before any vendor-board firmware work.
- Physical motherboard device-setup automation is firmware-defined and not universally writable from Windows.

## Firmware Policy Pipeline
- `scripts\10_probe_hardware.ps1` captures host inventory into `out\manifests`.
  - Optional: `-TryElevatedCollector` attempts an elevated fallback path if WMI/PnP inventory is sparse.
- `scripts\20_policy_plan.py` builds deterministic firmware policy plans in `out\plans`.
- `scripts\30_emit_os_handoff.py` emits `out\handoff\firmware_os_handoff_v1.json` for AxionOS enforcement and includes staged BIOS settings metadata from `out\handoff\pending_bios_settings_v1.json` when present.
- `scripts\50_build_hardware_capability_graph.py` maps inventory to vendor-agnostic rewrite capabilities and chipset adapter selection (`out\rewrite\capability_graph_v1.json`).
- `scripts\60_plan_signed_rewrite.py` builds signed rewrite plans with mandatory backup + A/B rollback guardrails (`out\rewrite\rewrite_plan_v1.json` + `out\rewrite\rewrite_signature_v1.json`).
- `scripts\70_execute_signed_rewrite.py` stages signed plan into inactive slot with rollback protection and controlled physical flash gating (`out\rewrite\rewrite_execution_report.json`).
- `policy\physical_flash_executor_policy_v1.json` defines the controlled physical flash lane (vendor/adaptor safety gates, operator ack, rollback enforcement, fail-closed by default for real command execution).
- `scripts\40_run_policy_pipeline.ps1` runs all three steps in order.
  - Example with deeper collector path enabled: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\40_run_policy_pipeline.ps1 -TryElevatedCollector`
  - Include rewrite planning: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\40_run_policy_pipeline.ps1 -TryElevatedCollector -EnableRewritePlanner`
  - Include rewrite staging execution: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\40_run_policy_pipeline.ps1 -TryElevatedCollector -EnableRewritePlanner -EnableRewriteExecution`

## Next phase (starter)
- Add hardware inventory + policy layer (no board flashing yet).
- Produce signed capability manifest per machine.
- Keep QEMU/OVMF as default validation loop before hardware targets.

