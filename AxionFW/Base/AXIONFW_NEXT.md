# AxionFW Next Steps (Practical + Safe)

## Goal
Move from UEFI scaffold to deterministic firmware policy tooling without touching physical board firmware yet.

## Phase A: Hardware Inventory (Host-side)
1. Enumerate SMBIOS/ACPI/PCI/USB/storage.
2. Normalize into a stable JSON capability manifest.
3. Hash + sign manifest for reproducibility.

Deliverables:
- scripts\10_probe_hardware.ps1
- out\manifests\<machine-id>.json
- out\manifests\<machine-id>.sha256
- Status: Implemented (host-side inventory emitter)

## Phase B: Policy Engine (Host-side)
1. Ingest capability manifest.
2. Select supported firmware/driver policy profile.
3. Emit plan artifact (no write).

Deliverables:
- scripts\20_policy_plan.py
- out\plans\<machine-id>.plan.json
- Status: Implemented (no-write policy planning)

## Phase B.1: Firmware->OS Handoff
1. Materialize a deterministic handoff artifact from firmware policy plan + firmware manifests.
2. Publish contract fields used by AxionOS runtime enforcement.

Deliverables:
- scripts\30_emit_os_handoff.py
- out\handoff\firmware_os_handoff_v1.json
- Status: Implemented (strict no-flash handoff emission)

## Phase C: Virtual Validation
1. Validate policy assumptions in QEMU/OVMF where possible.
2. Track pass/fail matrix and blockers.

Deliverables:
- out\validation\run_<timestamp>.json

## Guardrails
- No physical flashing in these phases.
- Every stage emits timestamped artifacts + hashes.
- Any future write stage must support rollback metadata.

## Phase D: Smart Rewrite Fabric (Inventory -> Adapter -> Signed Plan)
1. Build vendor-agnostic capability graph from inventory.
2. Auto-map unknown boards to safe generic rewrite primitives.
3. Select Intel/AMD/generic chipset bus adapter behind one contract.
4. Produce signed rewrite plan with mandatory backup + A/B rollback requirements.
5. Stage execution into inactive slot only; mark pending switch on reboot.

Deliverables:
- policy\hardware_rewrite_primitive_catalog_v1.json
- policy\chipset_bus_adapter_contract_v1.json
- scripts\50_build_hardware_capability_graph.py
- scripts\60_plan_signed_rewrite.py
- scripts\70_execute_signed_rewrite.py
- out\rewrite\capability_graph_v1.json
- out\rewrite\rewrite_plan_v1.json
- out\rewrite\rewrite_signature_v1.json
- out\rewrite\rewrite_execution_report.json
- out\rewrite\slot_state.json

Safety:
- Backup is mandatory before any staged rewrite step.
- A/B slot staging is mandatory.
- Rollback pointer to prior active slot is mandatory.
- Physical flash runs through a controlled fail-closed lane with adapter/vendor gates + operator ack + rollback enforcement; real flash commands remain disabled unless explicitly enabled by policy and runtime opt-in.
