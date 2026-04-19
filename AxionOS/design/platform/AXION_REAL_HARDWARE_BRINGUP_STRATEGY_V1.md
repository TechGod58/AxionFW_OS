# Axion Real Hardware Bring-Up Strategy v1

## Intent

AxionFW and AxionOS are still aiming for broad generic x64 support.

Starting with one real laptop family does not change that destination. It is a temporary proving-ground step so we can validate the generic hardware contract on recoverable hardware before scaling to many unrelated machines.

## Why one family first

- Real hardware failures cluster by storage, input, display, and power-management assumptions.
- A controlled first family keeps us from confusing platform-contract problems with fleet variation.
- Once the generic path survives one laptop family cleanly, we can widen deliberately to more laptops and then towers.

## First real-world family

The first real-world family is the HP 9470m/9480m bring-up track.

This family is used as:
- a recoverable laptop proving ground
- a source of hardware inventory for the generic x64 path
- a checkpoint before broader laptop and tower rollout

It is not used as:
- a permanent vendor-specific fork
- a reason to special-case the shell or installer UX
- proof that all x64 hardware is already supported

## Bring-up order

1. Keep QEMU q35 as the emulator contract reference.
2. Collect Windows-side hardware inventories from candidate laptops.
3. Validate the generic x64 UEFI firmware contract on the first laptop family.
4. Bring up storage, input, display console, security policy handling, and recovery path.
5. Only after those pass, widen to more laptop families.
6. After laptop widening, broaden to towers using the same generic contract.

## Required early wins

- UEFI boot path into AxionFW and AxionOS
- repair portal accessibility
- pre-boot auth handoff
- AHCI or other internal storage path
- keyboard and pointing-device usability
- framebuffer or console display
- secure-boot-policy and attestation path validation

## Data we should gather from each test machine

- BIOS/UEFI vendor and version
- CPU model and architecture
- chipset identity where available
- storage controller identity
- network controller identity
- secure-boot-policy availability
- graphics adapter identity
- battery presence for laptops
- input-device inventory

## Rule of thumb

The platform target remains generic x64.

The first laptop family is only the bridge from emulator confidence to real hardware confidence.
