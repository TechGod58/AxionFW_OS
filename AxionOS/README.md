# AxionOS Kernel + Runtime Baseline (x86_64 UEFI)

AxionOS is an actively-evolving OS/firmware stack with a contract-first runtime and release gate.

## Current Implementation Baseline

Kernel bring-up and ownership currently include:
- boot/early hook chain through `kmain()`
- memory subsystem with tracked allocator/release and stress cycles
- scheduler subsystem with policy ownership and syscall-guarded policy writes
- security subsystem with rule-precedence and stress assertions
- irq/time/ipc/bus/driver/userland lifecycle stage ownership
- runtime ownership (`e_runtime`, `qm`, `ig`, `ledger`, `qecc`) with smoke-gated checks

OS runtime and shell baseline currently include:
- Settings/Control Panel/Windows Tools host surfaces with shared action contract
- installer compatibility adapters (Windows/Linux) with replay signatures
- projection sessions (copy-on-write runtime layers + reconnect semantics)
- firewall guard with process-bound correlation, quarantine, adjudication, replay
- provenance fail-closed enforcement for installer/module intake
- optional ML anomaly sidecar behind feature flags
- firmware->OS handoff enforcement gate (contract + artifact + smart-driver + Parallel Cubed hardware guard checks)
- Parallel Cubed hardware guard hook generation for kernel bus/chipset enforcement

## Build (WSL/Ubuntu)

Prereqs:
- clang or gcc
- lld (recommended) or ld
- gnu-efi
- qemu-system-x86_64
- mtools (optional)

Install:
```bash
sudo apt update
sudo apt install -y build-essential clang lld gnu-efi qemu-system-x86 ovmf mtools
```

Build:
```bash
cd AxionOS
make
```

Run in QEMU (OVMF):
```bash
make run
```

## Verification

Release gate:
```powershell
.\tools\qa\run_release_gate.ps1
```

Kernel live verification (WSL wrapper):
```powershell
.\tools\repro\verify_kernel_wsl.ps1
```

Use `.\tools\qa\run_release_gate.ps1 -BuildProfile release` to include release-profile hardening checks, including live kernel boot and ML sidecar gating.

## Remaining Major Gaps

- broader real-hardware driver coverage beyond current baseline targets
- deeper gaming/media host surface completion
- continued UX polish and compatibility matrix expansion
