# OS Sandbox Promotion Pipeline v1

Goal: nothing writes to live OS/storage directly from workloads. All save-down flows through a deterministic security promotion path.

## 1) Pipeline States

1. **RUNNING_SANDBOX**
   - Workload executes in ephemeral VM/sandbox.

2. **EXPORT_REQUESTED**
   - Workload requests file/save export.

3. **STAGING_INBOX**
   - File transferred to internal local staging area (no email/text).

4. **SCAN_PHASE_1 (Integrity)**
   - Hash, signature, manifest, type validation.

5. **SCAN_PHASE_2 (Security)**
   - Malware/content scanning + heuristic checks.

6. **SCAN_PHASE_3 (Policy/IG)**
   - Invariant/policy enforcement (path, size, type, privilege constraints).

7. **PROMOTION_DECISION**
   - PASS -> promote
   - FAIL -> quarantine

8. **PLACED_OS_STORAGE**
   - Approved file moved to controlled target path.

9. **POST_PLACE_MONITOR**
   - Short probation watch; rollback/quarantine on anomaly.

## 2) Mandatory Rules

- No direct VM write access to host OS/user storage paths.
- All exports must carry correlation id and provenance metadata.
- Staging area is append-only input; only promoter service can move files out.
- Promotion is default-deny.
- Every decision is auditable and replayable.

## 3) Metadata Envelope (save-down event)

```json
{
  "corr": "corr_<uuid>",
  "component_id": "comp_<uuid>",
  "artifact_id": "art_<uuid>",
  "sha256": "...",
  "declared_type": "application/json",
  "requested_target": "safe://projects/...",
  "ts": "2026-03-01T14:00:00Z"
}
```

## 4) Decision Codes

- `PROMOTE_OK`
- `REJECT_SCHEMA`
- `REJECT_SIGNATURE`
- `REJECT_SCAN_MALWARE`
- `REJECT_POLICY`
- `REJECT_PATH`
- `QUARANTINED_REVIEW_REQUIRED`

## 5) Storage Zones

- **Zone A: Sandbox ephemeral** (destroy on close)
- **Zone B: Staging inbox** (untrusted, non-executable)
- **Zone C: Quarantine** (isolated, analyst-only)
- **Zone D: Approved OS storage** (trusted placement)

## 6) Minimal v1 Implementation Order

1. Define `safe://` target mapping rules.
2. Implement local staging inbox + promotion daemon.
3. Integrate schema/hash/signature checks.
4. Integrate scanner chain.
5. Integrate IG/policy gate.
6. Emit append-only promotion audit log.
7. Add rollback/quarantine hooks.

## 7) Success Criteria

- Closing sandbox destroys unsaved payloads.
- Any persisted file has full promotion audit trail.
- No bypass path from sandbox to Zone D.
- Replaying promotion log reproduces same allow/deny outcome.
