# App VM Enforcement Integration v1

- Added runtime app scaffolds under `<AXIONOS_ROOT>\runtime\apps\*`
- Added VM enforcement policy: `<AXIONOS_ROOT>\config\APP_VM_ENFORCEMENT_V1.json`
- Added launcher policy resolver: `<AXIONOS_ROOT>\runtime\capsule\launchers\app_launcher_policy.py`

## Notes
- Most user apps default to capsule mode.
- Core system daemons remain host-required.
- Registry editor uses guarded elevated capsule mode.
- Persistence remains promotion-gated.

