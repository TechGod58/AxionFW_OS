# AXION Control Surface v1

Purpose: operator-first control UI for AxionOS runtime (VM orchestration + promotion security) without distro-style complexity.

---

## 1) Design Goals

- **See system state at a glance** (no hidden automation)
- **One-step traceability** from VM action -> save-down verdict -> storage placement
- **Fast intervention** during risk events (queue pressure, quarantine, policy deny)
- **Board-agnostic operations** (same control plane regardless of hardware target)

---

## 2) Primary Layout (4-pane tactical surface)

```text
+-----------------------------------------------------------------------------------+
| AXION CONTROL SURFACE                                                            |
| Status: ACTIVE   Host Load: 42% CPU / 58% MEM   Policy: SAFE_URI_V1  IG: ONLINE |
+---------------------------------+-------------------------------+-----------------+
| WORKLOADS                       | PROMOTION QUEUE               | SECURITY STATE  |
|---------------------------------|-------------------------------|-----------------|
| vm-001  RUN  small  stable      | req-991  pending  projects   | IG: PASS        |
| vm-002  RUN  medium latency     | req-992  queued   artifacts   | Scan: PASS      |
| vm-003  QUEUE throughput        | req-993  denied   bad_zone    | Quarantine: 3   |
| vm-004  DENY  bad class         | req-994  promoted userdocs    | Last Alert: ... |
+---------------------------------+-------------------------------+-----------------+
| RESOURCE GRID / DECISIONS                                                     |
|-------------------------------------------------------------------------------|
| corr_xxx  ALLOCATE  vcpu=2 mem=4096 prio=80  reason=ALLOC_OK                 |
| corr_yyy  QUEUE     retry=15s                 reason=ALLOC_HOST_PRESSURE      |
| corr_zzz  DENY                                 reason=ALLOC_BAD_CLASS         |
+-------------------------------------------------------------------------------+
| Actions: [Retry] [Kill Sandbox] [Quarantine Review] [Promote(if allowed)]     |
|          [Export Audit] [Open Corr Trace]                                     |
+--------------------------------------------------------------------------------+
```

---

## 3) Wireframe Blocks

### A) Header Bar

Displays:
- runtime mode (`ACTIVE` / `DEGRADED` / `MAINTENANCE`)
- host pressure snapshot (CPU/MEM)
- policy profile ids (`SAFE_URI_POLICY_V1`, promotion policy version)
- IG channel status (`ONLINE` / `OFFLINE` / `FAILSAFE`)

### B) Workloads Pane

Each row:
- vm id
- state (`RUN`, `QUEUE`, `DENY`, `THROTTLE`)
- vm class (`small|medium|large`)
- workload class
- corr id (hover/expand)

Quick actions per row:
- kill
- throttle
- open trace

### C) Promotion Queue Pane

Each entry:
- request id
- phase (`STAGED`, `SCAN`, `IG`, `PROMOTE`, `QUARANTINE`)
- target `safe://` URI
- decision code (if terminal)

Quick actions:
- retry (non-terminal failures)
- quarantine review
- promote override (only if policy permits + role allows)

### D) Security State Pane

Cards:
- IG verdict stream (last N)
- scanner pass/fail ratio
- quarantine count + newest reason code
- policy violations trend (hour/day)

### E) Resource Grid Pane

Shows allocator decisions with deterministic reason codes:
- `ALLOC_OK`
- `ALLOC_HOST_PRESSURE`
- `ALLOC_BAD_CLASS`

Columns:
- corr
- decision
- resource assignment
- reason
- timestamp

---

## 4) Interaction Flow

### Flow 1: Normal Save-Down (happy path)

1. VM workload creates artifact.
2. Artifact enters staging inbox.
3. Promotion pipeline evaluates (schema -> hash -> safe:// -> scan -> IG).
4. UI shows phase transitions live.
5. Decision `PROMOTE_OK` appears with resolved path.
6. Corr trace links allocator + promotion audit records.

### Flow 2: Queue under host pressure

1. New workload request arrives.
2. Allocator returns `QUEUE` (`ALLOC_HOST_PRESSURE`).
3. UI highlights workload row amber and sets retry countdown.
4. Operator can wait, reprioritize, or kill competing VM.

### Flow 3: Deny for invalid class

1. Workload request uses unsupported vm class.
2. Allocator returns `DENY` (`ALLOC_BAD_CLASS`).
3. UI marks request red with direct fix hint (valid classes).

### Flow 4: IG-gated quarantine

1. Promotion reaches IG gate.
2. IG returns fail (`REJECT_IG`).
3. Artifact moved to quarantine.
4. Security pane increments quarantine count + reason code.
5. Operator can open quarantine review with corr-linked evidence.

---

## 5) Visual Language (Axion identity)

### Palette (v1)

- **Axion Blue** `#2EA8FF` -> healthy/active flow
- **Signal Amber** `#F4B942` -> queued/throttled/warning
- **Hard Red** `#FF4D4F` -> deny/quarantine/fail
- **Qh8 Purple Accent** `#7A5CFF` -> strategic events / check-checkmate markers
- **Dark Base** `#0B1020` -> background
- **Panel Base** `#121A2C` -> cards/panes

### Typography

- UI font: clean sans (Inter/Segoe UI class)
- Numeric telemetry: monospace for alignment
- Reason codes uppercase monospace chips

### Iconography

- shield = security verdict
- grid = resource allocation
- cube = sandbox/workload
- arrow-down-in-box = promotion placement
- chess king marker = Qh8# strategic signal

### State Chips

- `RUN` (blue)
- `QUEUE` (amber)
- `DENY` (red)
- `PROMOTED` (blue)
- `QUARANTINED` (red)

---

## 6) Operator Controls (minimal set)

Global:
- Retry
- Kill Sandbox
- Quarantine Review
- Export Audit
- Open Corr Trace

Contextual (role-gated):
- Promote Override (disabled by default)

Rule: no hidden destructive actions. Any kill/quarantine/promote action must produce an audit event with corr id.

---

## 7) Correlation Trace Panel

Open by corr id and show unified timeline:
- allocator decision
- promotion stages
- final storage/quarantine location
- reason codes
- timestamps

This is the core trust feature: **one corr id = one end-to-end truth path**.

---

## 8) v1 Non-Goals

- app store/package manager UX
- desktop shell customization
- full theming engine
- multi-tenant RBAC matrix

---

## 9) Build-Ready UI Data Contracts (starter)

### Workload item

```json
{
  "vm_id": "vm-001",
  "state": "RUN",
  "vm_class": "small",
  "workload_class": "stability_critical",
  "corr": "corr_abc"
}
```

### Promotion item

```json
{
  "request_id": "req-991",
  "phase": "SCAN",
  "safe_uri": "safe://projects/axionos/e2e/report.json",
  "decision": null,
  "corr": "corr_abc"
}
```

### Security card

```json
{
  "ig_status": "ONLINE",
  "scan_pass_rate": 0.98,
  "quarantine_count": 3,
  "last_reason": "REJECT_IG"
}
```

---

## 10) Immediate Next UI Deliverables

1. `AXION_CONTROL_SURFACE_COMPONENT_MAP_V1.md` (component IDs/events)
2. `AXION_CONTROL_SURFACE_STATES_V1.json` (state machine definitions)
3. low-fi clickable mock (single-screen) using these pane contracts

