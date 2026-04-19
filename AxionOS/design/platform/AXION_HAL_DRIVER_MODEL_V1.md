# AxionHAL Driver Model v1

AxionHAL is the hardware adaptation layer that turns AxionFW and AxionOS into one platform instead of two neighboring projects.

## Purpose

- Give AxionFW a clear boot and trust contract to hand to AxionOS.
- Separate motherboard support from sandbox mediation, so we do not mix board bring-up with user-facing app isolation.
- Keep QEMU `q35` as the first reference target while we grow toward broader x64 UEFI motherboard support.

## Driver families

1. `firmware_handoff`
   Reads UEFI, ACPI, runtime variables, and measured-boot state from AxionFW.
2. `motherboard_core`
   Owns chipset, interrupt, timer, bus, storage-controller, and power-management bring-up.
3. `device_io`
   Owns functional drivers like storage, network, USB, audio, and display.
4. `security_trust`
   Owns Secure Boot state, attestation, rollback policy, and trust refresh.
5. `sandbox_mediation`
   Bridges host devices and permanent profile sandboxes into capsules without breaking the core isolation model.

## Board support packages

Every supported board family should ship as a Board Support Package, or BSP.

A BSP includes:

- compatible firmware profile
- compatible AxionOS boot profile
- required driver-class coverage
- installer flow
- recovery guidance

## Driver creator

The driver creator is not a compiler replacement. It is a scaffold tool that generates a signed-package skeleton, metadata, and test placeholders for:

- motherboard drivers
- device drivers
- sandbox mediation drivers

This keeps new driver work aligned with the AxionHAL contract instead of creating one-off packages.

## Installer order

1. Detect supported hardware or BSP match.
2. Validate firmware-to-OS contract compatibility.
3. Install or stage firmware payload.
4. Install driver bundle for the matched BSP.
5. Install AxionOS payload.
6. Finalize security policy handoff.

## Current state

This repo now contains the contract, BSP catalog, bundle builder, and driver-kit scaffold needed to grow the platform deliberately.

It does not yet contain a full real-world motherboard driver set for arbitrary x64 machines. QEMU `q35` remains the reference bring-up target.
