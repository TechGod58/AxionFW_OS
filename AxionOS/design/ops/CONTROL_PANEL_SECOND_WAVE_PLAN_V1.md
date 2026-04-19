# CONTROL_PANEL_SECOND_WAVE_PLAN_V1

## Status
- Wave-2 planning locked (contract-first).
- Execution model: one panel slice at a time, with deterministic FAIL/PASS proof before advancing.

## Locked Slice Template (per panel)
1. Contract schema
   - `contracts/compat/<panel>/v1/<panel>.schema.json`
2. Registry integration
   - Add/update entry in `contracts/registry/index.json`
   - Run `python <AXIONOS_ROOT>\tools\contracts\validate_registry.py`
   - Acceptance: `REG_EXIT=0`
3. Runtime flow
   - `tools/runtime/<panel>_flow.py`
4. Runtime artifacts
   - `out/runtime/<panel>_audit.json`
   - `out/runtime/<panel>_smoke.json`
5. Contract report integration
   - Add section to deterministic emitter:
     - `<panel>: { status, audit_path, smoke_path, failures[] }`
6. Deterministic negative control
   - One stable failure code + deterministic non-zero exit code
   - Emit FAIL contract report and PASS contract report

## Contract-First Acceptance Gates
A panel slice is CLOSED only when all are true:
- Schema exists under versioned path (`/v1/` or appropriate major path).
- Registry entry exists and remains sorted/stable.
- Registry validator passes (`REG_EXIT=0`).
- Runtime flow executes and emits smoke + audit artifacts.
- Report section exists with `failures` always serialized as JSON array.
- Negative control proven in FAIL run (expected code + expected exit).
- PASS run proven (`failures=[]`, exit 0).

## Deterministic Failure Code Policy
- Each panel owns a unique, stable failure code namespace.
- One canonical negative control code required per slice.
- Failures are always JSON arrays:
  - PASS: `[]`
  - FAIL: `[ {"code":"...", ...} ]`
- Exit-code mapping is deterministic and documented in runtime flow.

## Artifact Requirements
Per slice, retain full-path evidence for:
- Schema path
- Runtime flow path
- Smoke + audit artifact paths
- FAIL/PASS report paths
- Validator outcome (`REG_EXIT=0`)

## Registry Integration Rule
- Registry is authoritative.
- Every new panel contract must be registered with:
  - stable `contract_id`
  - `category=schema`
  - semantic `version`
  - versioned `path`
  - `sha256`
- Maintain uniqueness and sorted order (`contract_id`, `version`).

## Wave-2 Candidate Queue (locked order)
1. Permissions / Policy Panel
2. System Info Panel
3. Power / Energy Panel
4. Backup / Restore Panel
5. Logs / Diagnostics Panel
6. Developer Tools Panel

## Seed Deterministic Negative Controls
1. permissions_policy_panel: `PERMISSION_POLICY_INVALID`
2. system_info_panel: `SYSTEM_INFO_SOURCE_UNAVAILABLE`
3. power_energy_panel: `POWER_PROFILE_UNSUPPORTED`
4. backup_restore_panel: `BACKUP_TARGET_INVALID`
5. logs_diagnostics_panel: `DIAGNOSTIC_CHANNEL_DENIED`
6. developer_tools_panel: `DEVTOOLS_MODE_BLOCKED`

## Execution Notes
- No scope expansion or refactor during a slice.
- Deterministic full-file emitter writes only.
- Report in strict format: `DONE / EVIDENCE / BLOCKER / NEXT`.

## Wave-2 closure status (2026-03-05T10:44:51.4340696Z)
- [x] 1. permissions_panel
- [x] 2. system_info_panel
- [x] 3. power_energy_panel
- [x] 4. backup_restore_panel
- [x] 5. logs_diagnostics_panel
- [x] 6. developer_tools_panel

## Wave-2 artifact references
- Completion artifact: <AXIONOS_ROOT>\out\contracts\control_panel_second_wave_complete.json
- Final FAIL report: <AXIONOS_ROOT>\out\contracts\contract_report_AXION_BUILD_20260305T104352Z_DEVELOPER_TOOLS_PANEL_FAIL.json
- Final PASS report: <AXIONOS_ROOT>\out\contracts\contract_report_AXION_BUILD_20260305T104353Z_DEVELOPER_TOOLS_PANEL_PASS.json
- Registry validation artifact: <AXIONOS_ROOT>\out\contracts\registry_validation.json
- Invariant: all panel ailures fields serialized as JSON arrays ([] or [ {"code": ...} ])

