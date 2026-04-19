# AXION Control Surface Component Map v1

Purpose: map UI components to runtime data/events so implementation is deterministic.

Related:
- `AXION_CONTROL_SURFACE_V1.md`
- allocator runtime (`<AXIONOS_ROOT>\runtime\allocator\`)
- promotion runtime (`<AXIONOS_ROOT>\runtime\promotion\`)

---

## 1) Screen Composition

```text
AXION_CONTROL_SURFACE_ROOT
 ├─ HEADER_STATUS_BAR
 ├─ PANE_WORKLOADS
 ├─ PANE_PROMOTION_QUEUE
 ├─ PANE_SECURITY_STATE
 ├─ PANE_RESOURCE_GRID
 ├─ ACTION_BAR
 └─ CORR_TRACE_DRAWER
```

---

## 2) Component IDs + Data Contracts

## 2.1 `HEADER_STATUS_BAR`

**Component ID:** `cs.header.status`

**Inputs:**
- host load snapshot
- policy ids
- IG channel status
- runtime mode

**Model:**

```json
{
  "runtime_mode": "ACTIVE",
  "host": {"cpu_used": 0.42, "mem_used": 0.58},
  "policy": {"safe_uri": "SAFE_URI_POLICY_V1", "promotion": "PROMOTION_POLICY_V1"},
  "ig": {"status": "ONLINE"}
}
```

**Events out:** none (display-only in v1)

---

## 2.2 `PANE_WORKLOADS`

**Component ID:** `cs.pane.workloads`

**Inputs:** allocator/workload registry stream

**Row model:**

```json
{
  "vm_id": "vm-001",
  "state": "RUN",
  "vm_class": "small",
  "workload_class": "stability_critical",
  "corr": "corr_abc",
  "updated_at": "2026-03-01T16:00:00Z"
}
```

**Actions/events out:**
- `workload.kill.requested`
- `workload.throttle.requested`
- `corr.trace.opened`

---

## 2.3 `PANE_PROMOTION_QUEUE`

**Component ID:** `cs.pane.promotion_queue`

**Inputs:** promotion pipeline stage stream + decision output

**Row model:**

```json
{
  "request_id": "req-991",
  "phase": "SCAN",
  "safe_uri": "safe://projects/axionos/e2e/report.json",
  "decision": null,
  "corr": "corr_abc",
  "updated_at": "2026-03-01T16:00:02Z"
}
```

**Actions/events out:**
- `promotion.retry.requested`
- `promotion.quarantine_review.requested`
- `promotion.override.requested` (role-gated)
- `corr.trace.opened`

---

## 2.4 `PANE_SECURITY_STATE`

**Component ID:** `cs.pane.security`

**Inputs:** IG stream + scan stream + quarantine metrics

**Model:**

```json
{
  "ig_status": "ONLINE",
  "scan_pass_rate": 0.98,
  "quarantine_count": 3,
  "last_reason": "REJECT_IG",
  "violations_1h": 2
}
```

**Actions/events out:**
- `security.quarantine.opened`
- `security.export_audit.requested`

---

## 2.5 `PANE_RESOURCE_GRID`

**Component ID:** `cs.pane.resources`

**Inputs:** allocator decisions (`ALLOCATE|QUEUE|DENY|THROTTLE`)

**Row model:**

```json
{
  "corr": "corr_e2e_queue_001",
  "decision": "QUEUE",
  "vcpu": null,
  "mem_mb": null,
  "reason": "ALLOC_HOST_PRESSURE",
  "retry_sec": 15,
  "ts": "2026-03-01T16:00:10Z"
}
```

**Actions/events out:**
- `resource.retry.requested`
- `corr.trace.opened`

---

## 2.6 `ACTION_BAR`

**Component ID:** `cs.actions.global`

**Buttons:**
- Retry
- Kill Sandbox
- Quarantine Review
- Export Audit
- Open Corr Trace

**Events out:**
- `global.retry.requested`
- `global.kill_sandbox.requested`
- `global.quarantine_review.requested`
- `global.audit_export.requested`
- `corr.trace.opened`

---

## 2.7 `CORR_TRACE_DRAWER`

**Component ID:** `cs.drawer.corr_trace`

**Input:** corr id

**Output timeline model:**

```json
{
  "corr": "corr_e2e_alloc_001",
  "events": [
    {"source":"allocator","decision":"ALLOCATE","code":"ALLOC_OK","ts":"..."},
    {"source":"promotion","decision":"PROMOTE_OK","path":"C:\\AxionOS\\data\\projects\\...","ts":"..."}
  ]
}
```

**Actions/events out:**
- `corr.trace.exported`

---

## 3) Event Bus Topics (UI-facing)

Subscribe topics:
- `telemetry.host.snapshot`
- `allocator.decision`
- `promotion.stage`
- `promotion.decision`
- `security.ig.verdict`
- `security.scan.verdict`
- `security.quarantine.metrics`

Publish topics:
- `ui.workload.kill`
- `ui.workload.throttle`
- `ui.promotion.retry`
- `ui.promotion.override`
- `ui.audit.export`
- `ui.corr.trace.open`

---

## 4) Decision Code Mapping (UI chip text)

Allocator:
- `ALLOC_OK` -> "Allocated"
- `ALLOC_HOST_PRESSURE` -> "Queued (Host Pressure)"
- `ALLOC_BAD_CLASS` -> "Denied (Invalid VM Class)"

Promotion:
- `PROMOTE_OK` -> "Promoted"
- `REJECT_SCHEMA` -> "Rejected: Schema"
- `REJECT_HASH` -> "Rejected: Hash"
- `REJECT_POLICY` -> "Rejected: Policy"
- `REJECT_SCAN` -> "Rejected: Scanner"
- `REJECT_IG` -> "Rejected: IG"

safe:// map:
- `MAP_FAIL_SCHEME`, `MAP_FAIL_ZONE`, `MAP_FAIL_TRAVERSAL`, `MAP_FAIL_ESCAPE_DETECTED`

---

## 5) Refresh + Retention Rules

- Header + metrics: 1s refresh target
- Grid panes: event-driven append/update
- Corr drawer: on-demand fetch + cached 2 min
- UI retention: last 500 rows/pane (v1)

---

## 6) Error Display Rules

- Never hide reason codes.
- Every deny/reject must show:
  - machine code
  - human label
  - corr id
- If data source unavailable, show `DEGRADED` with explicit missing topic names.

---

## 7) Build Order (implementation)

1. static shell + pane containers
2. bind allocator decision stream to Resource Grid
3. bind promotion decision stream to Promotion Queue
4. add Corr Trace drawer with joined audits
5. wire operator actions (retry/kill/export)
6. apply visual language + Qh8# accent markers

---

## 8) v1 Definition of Done

- Operator can observe `ALLOCATE/QUEUE/DENY` live.
- Operator can observe `PROMOTE/QUARANTINE` live.
- Operator can open corr trace for any row and see allocator + promotion chain.
- All critical actions emit auditable events.


