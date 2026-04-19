# AXION Sandboxed Update/Install Flow v1

Purpose: all app/program installs and updates are validated in VM sandbox before OS placement.

## Required flow
1. Package arrives (download/import/media)
2. Ingress threat scan (pre-port + port + staging)
3. Spawn install-test capsule VM
4. Build/provide required runtime environment from app blueprint
5. Run installer/update inside capsule only
6. Observe behavior (files, registry/config, network, privilege requests)
7. Run policy + IG + scanner verdict checks
8. If pass: generate signed install plan for host OS
9. Host executes controlled install plan via promotion gate
10. Post-install probation monitor + rollback hooks

## Hard rules
- No direct installer execution on trusted OS path.
- No bypass around promotion gate.
- All install/update actions corr-traced and auditable.
- Fail at any stage => quarantine package + block install.

## Decision codes
- `UPD_OK`
- `UPD_QUEUE_ANALYSIS`
- `UPD_REJECT_SCAN`
- `UPD_REJECT_POLICY`
- `UPD_REJECT_IG`
- `UPD_QUARANTINE`

## Definition of Done
- Every install/update path uses capsule test first.
- Trusted OS changes occur only from approved install plan.
