# safe:// URI Mapping Spec v1

Purpose: define non-bypassable placement rules for promoted artifacts from sandbox pipeline into OS storage.

## 1) Principles

- `safe://` is the only accepted target scheme for promotions.
- Callers never submit raw host filesystem paths.
- Mapping is deterministic, policy-controlled, and auditable.
- Any unresolved or disallowed mapping is hard-fail.

## 2) URI Format

```text
safe://<zone>/<namespace>/<relative_path>
```

Examples:
- `safe://projects/axionos/build/report.json`
- `safe://userdocs/notes/today.md`
- `safe://artifacts/qecc/run_2026_03_01/summary.json`

## 3) Allowed Zones (v1)

- `projects`
- `userdocs`
- `artifacts`
- `imports`

Disallowed zones (hard fail):
- `system`
- `windows`
- `boot`
- `drivers`
- `registry`

## 4) Host Mapping Table (example)

| safe zone | Host root (example) |
|---|---|
| projects | `<AXIONOS_ROOT>\data\projects` |
| userdocs | `<AXIONOS_ROOT>\data\userdocs` |
| artifacts | `<AXIONOS_ROOT>\data\artifacts` |
| imports | `<AXIONOS_ROOT>\data\imports` |

> Note: final roots should be set by OS config, not hardcoded in callers.

## 5) Validation Rules

1. Scheme must be exactly `safe://`.
2. Zone must be in allowlist.
3. `relative_path` must not be empty.
4. Reject traversal tokens (`..`, leading slash, drive letters, UNC paths).
5. Normalize separators to canonical form before mapping.
6. Enforce extension/type policy by zone.
7. Enforce max size by zone and MIME category.

## 6) Mapping Algorithm (deterministic)

1. Parse URI -> `{zone, namespace, relative_path}`.
2. Validate tokens against allowlist/regex.
3. Canonicalize path.
4. Join with zone root from trusted config.
5. Re-check joined result is still under zone root (anti-escape check).
6. Return resolved host path + policy profile id.

## 7) Decision Codes

- `MAP_OK`
- `MAP_FAIL_SCHEME`
- `MAP_FAIL_ZONE`
- `MAP_FAIL_PATH_EMPTY`
- `MAP_FAIL_TRAVERSAL`
- `MAP_FAIL_POLICY_TYPE`
- `MAP_FAIL_POLICY_SIZE`
- `MAP_FAIL_ESCAPE_DETECTED`

## 8) Audit Requirements

Each promotion decision logs:
- original `safe://` URI
- resolved host path (or fail code)
- policy profile id
- correlation id
- artifact hash
- decision timestamp

## 9) v1 Non-Goals

- Cross-machine URI routing
- Network shares as direct targets
- Dynamic zone creation by untrusted callers

## 10) Quick Test Cases

### PASS
- `safe://projects/axionos/build/out.json`
- `safe://artifacts/qecc/run42/ttf_summary.json`

### FAIL
- `C:\Windows\System32\...` (not safe scheme)
- `safe://system/kernel.bin` (disallowed zone)
- `safe://projects/../windows/win.ini` (traversal)
- `safe://projects//` (empty relative path)

