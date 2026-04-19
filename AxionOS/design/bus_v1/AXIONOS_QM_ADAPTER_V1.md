# AxionOS-QM Adapter v1

Status: Draft
Goal: translate AxionOS bus contract calls into QM-compatible runtime semantics without importing full QM complexity into OS core.

## 1) Adapter Scope

### In Scope (v1)
- component.register -> QM component admission
- component.heartbeat -> QM health update
- route.request -> QM route decision request
- component.fault -> QM fault ingest
- component.quarantine -> QM containment action
- ig.verdict passthrough to admission/quarantine pipeline

### Out of Scope (v1)
- predictive/bandit auto-tuning
- phase sweep orchestration
- long-horizon policy evolution
- offline analytics/reporting

## 2) Translation Map

| AxionOS Type | Adapter Action | QM Semantic |
|---|---|---|
| component.register | normalize + validate + admit | runtime component registry add |
| component.heartbeat | normalize health envelope | runtime state update |
| route.request | compile constraints | route planner decision |
| component.fault | classify severity | risk/fault engine ingest |
| component.quarantine | enforce TTL + state lock | safe-mode/quarantine |
| ig.verdict | gate admission/continuation | invariant policy verdict |

## 3) Adapter Interface (OS side)

```text
submit(message) -> {accepted: bool, reason?: str, output?: object}
replay(correlation_id) -> ordered message/decision chain
health() -> adapter health + backlog + last_error
```

## 4) Failure Semantics

- Invalid envelope/schema -> reject (`accepted=false`, reason=`schema_error`)
- IG fail on admission -> reject + optional quarantine command
- Route unavailable -> deny route with deterministic reason code
- Critical fault -> quarantine command emitted immediately

## 5) Determinism Requirements

- Same input envelope set + same policy snapshot => same route output.
- All adapter decisions emit correlation-linked audit records.
- No hidden mutable global state outside explicit snapshot.

## 6) First Acceptance Tests

1. Register -> Heartbeat -> Route -> Success path.
2. Register with IG fail -> admission denied.
3. Active component critical fault -> quarantine emitted.
4. Replay of route correlation returns identical decision payload.

## 7) Next Artifact

`fixtures/bus_v1/adapter_flow/` with chained scenario fixtures for:
- happy path
- IG fail path
- fault quarantine path
