# AxionOS ↔ AxionBus Contract v1 (Draft)

Status: Draft (implementation-ready baseline)
Scope: OS-side contract for dynamic component lifecycle + routing + safety gating.

## 1) Design Goals

- Keep motherboard/firmware deterministic and hardware-agnostic.
- Move adaptive orchestration to bus/runtime layer.
- Support on-the-fly component creation and teardown.
- Enforce safety/invariants at admission and during runtime.
- Keep messages replayable and auditable.

## 2) Envelope (all bus messages)

```json
{
  "v": 1,
  "type": "<message_type>",
  "id": "msg_<uuid>",
  "ts": "2026-03-01T13:30:00Z",
  "source": "axionos",
  "target": "axionbus",
  "corr": "corr_<uuid>",
  "payload": {}
}
```

Required fields:
- `v`: protocol version (int)
- `type`: message type (string)
- `id`: unique message id (string)
- `ts`: ISO-8601 UTC timestamp
- `source`: sender id
- `target`: receiver id
- `corr`: correlation id for request/response groups
- `payload`: type-specific object

## 3) Core Message Types

### 3.1 RegisterComponent
Type: `component.register`

Payload:
```json
{
  "component_id": "comp_<uuid>",
  "component_kind": "vm|service|driver|worker",
  "contract_version": "1.0.0",
  "capabilities": ["compute.cpu", "io.net"],
  "resource_hints": { "cpu": 2, "mem_mb": 2048 },
  "labels": { "tenant": "local", "priority": "normal" }
}
```

Response: `component.registered | component.rejected`

### 3.2 Heartbeat
Type: `component.heartbeat`

Payload:
```json
{
  "component_id": "comp_<uuid>",
  "state": "warmed|active|degraded|quarantined",
  "health": { "ok": true, "score": 0.98 },
  "metrics": { "lat_ms": 7.2, "err_rate": 0.001 }
}
```

### 3.3 CapabilityUpdate
Type: `component.capability.update`

Payload:
```json
{
  "component_id": "comp_<uuid>",
  "capabilities_add": ["qecc.decode"],
  "capabilities_remove": ["io.usb.raw"]
}
```

### 3.4 RouteRequest
Type: `route.request`

Payload:
```json
{
  "job_id": "job_<uuid>",
  "workload_class": "latency_sensitive|stability_critical|throughput_heavy",
  "requirements": ["compute.cpu"],
  "safety_profile": "default",
  "deadline_ms": 200,
  "input_ref": "blob://..."
}
```

Response: `route.assigned | route.denied`

### 3.5 FaultReport
Type: `component.fault`

Payload:
```json
{
  "component_id": "comp_<uuid>",
  "severity": "warn|error|critical",
  "code": "RUNTIME_INVARIANT_TRIP",
  "detail": "fail_max exceeded",
  "telemetry_ref": "blob://..."
}
```

### 3.6 QuarantineCommand
Type: `component.quarantine`

Payload:
```json
{
  "component_id": "comp_<uuid>",
  "reason": "invariant_violation",
  "ttl_sec": 300,
  "allow_rejoin": true
}
```

## 4) Lifecycle FSM

States:
- `Created`
- `Warmed`
- `Active`
- `Degraded`
- `Quarantined`
- `Retired`

Transitions:
- Created -> Warmed (register success)
- Warmed -> Active (IG admission pass)
- Active -> Degraded (health drop/fault warn)
- Degraded -> Active (recovery criteria met)
- Active|Degraded -> Quarantined (critical invariant/fault)
- Quarantined -> Warmed (rejoin allowed + checks pass)
- Any -> Retired (explicit teardown)

## 5) Safety Gates (IG integration points)

IG checks required at:
- component registration admission
- route assignment pre-flight
- runtime periodic guard (heartbeat window)
- fault-triggered quarantine decision

Mandatory IG verdict fields:
- `verdict`: `pass|warn|fail`
- `policy_id`
- `rule_hits` (array)
- `reason`

## 6) Replay/Audit Requirements

- Every message append-only to NDJSON bus log.
- Correlation ids must chain request->decision->execution->result.
- Deterministic replay mode must allow:
  - route decision re-evaluation
  - IG verdict verification
  - lifecycle reconstruction by timestamp

## 7) OS Implementation Plan (next)

1. Implement envelope serializer/deserializer in AxionOS runtime.
2. Implement component FSM in OS runtime core.
3. Add IG check hook interfaces (stub -> live).
4. Add route.request + route.assigned handling.
5. Emit structured audit NDJSON from OS side.

## 8) Non-Goals for v1

- Physical flashing or firmware writes.
- Cross-machine federation.
- Full cryptographic signing pipeline.

---

If this draft is accepted, next artifact should be `AXIONOS_BUS_CONTRACT_V1.schema.json` + an OS-side message test matrix.
