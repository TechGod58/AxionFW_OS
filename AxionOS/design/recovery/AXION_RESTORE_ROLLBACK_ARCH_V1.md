# AXION Restore & Rollback Architecture v1

Purpose: define destructive/non-destructive restore paths plus shadow-copy rollback model, aligned with capsule-first runtime.

## 1) Restore Modes

### A) Non-Destructive Restore (default)

Use when:
- app/runtime corruption
- bad update
- policy regression
- user data should be preserved

Behavior:
1. Freeze affected services/capsules
2. Restore system runtime state from last known-good checkpoint
3. Rebind configs/policies to checkpoint version
4. Preserve user data zones (`safe://userdocs`, approved project data)
5. Re-run health checks
6. Resume services

Output codes:
- `RESTORE_ND_OK`
- `RESTORE_ND_PARTIAL`
- `RESTORE_ND_FAIL`

### B) Destructive Restore (last resort)

Use when:
- severe compromise/integrity failure
- unrecoverable policy/runtime drift
- explicit operator approval

Behavior:
1. Boot to secure recovery environment
2. Reimage core runtime/system partitions from trusted signed baseline
3. Rehydrate only approved user data snapshots
4. Rebuild service registry and policy defaults
5. Require admin re-attestation/logon before normal boot

Output codes:
- `RESTORE_D_OK`
- `RESTORE_D_REIMAGE_FAIL`
- `RESTORE_D_REHYDRATE_FAIL`

## 2) Shadow Copy Rollback Model

- Every install/update/policy change creates a shadow checkpoint.
- Checkpoints store:
  - runtime manifest hash
  - policy/config versions
  - service states
  - capsule framework layer references
  - optional user data snapshot pointers

Checkpoint types:
- `pre_update`
- `post_update`
- `pre_policy_change`
- `pre_driver_promote`

Rollback flow:
1. Select checkpoint by corr id / timestamp
2. Validate checkpoint integrity
3. Apply rollback atomically
4. Verify health and invariant pass
5. Log rollback decision + outcome

## 3) Capsule/VM Advantage Integration

- App-level rollback is lightweight:
  - discard bad capsule overlay
  - relaunch from known-good framework layer
- System-level rollback still uses checkpoint/reimage model.
- Persistent writes already mediated by promotion gate, reducing rollback blast radius.

## 4) Data Protection Rules

- Core system rollback must never auto-delete approved user docs without explicit destructive consent.
- Quarantine store persists across non-destructive restore.
- Destructive restore can optionally purge quarantine (operator choice, audited).

## 5) Operator Controls

- `restore non-destructive --target <scope> --checkpoint <id>`
- `restore destructive --baseline <version> --confirm <token>`
- `rollback --corr <id>`
- `checkpoint list`

All commands require role-appropriate auth + corr-trace audit.

## 6) Definition of Done (v1)

- Non-destructive restore recovers from bad update while preserving user data.
- Destructive restore reimages core from signed baseline with explicit confirmation.
- Shadow-copy checkpoints support deterministic rollback by corr id.
- Restore and rollback outcomes visible in TraceView/Control Surface.
