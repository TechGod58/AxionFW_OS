# AxionOS Bus Contract v1 — Message Test Matrix

Purpose: minimal validation matrix to prove protocol correctness before live integration.

## Legend
- PASS = expected acceptance behavior
- FAIL = expected rejection behavior
- IG = invariant guard

---

## A) Envelope Validation

1. Valid envelope + known `type` -> PASS
2. Missing `corr` -> FAIL
3. `v != 1` -> FAIL
4. Invalid `ts` format -> FAIL
5. Unknown `type` -> FAIL

## B) component.register

1. Valid VM registration with capabilities -> PASS
2. Missing `component_id` -> FAIL
3. Invalid `component_kind` value -> FAIL
4. Empty capabilities array -> PASS (warn only, policy decision)
5. Oversized resource_hints (out-of-policy) -> PASS envelope / IG WARN or FAIL

## C) component.heartbeat

1. Active heartbeat with health score -> PASS
2. Missing `health.ok` -> FAIL
3. Invalid `state` -> FAIL
4. Degraded + high error rate -> PASS envelope / IG WARN

## D) component.capability.update

1. Add QECC capability -> PASS
2. Remove non-existent capability -> PASS (idempotent)
3. Empty add/remove sets -> PASS (no-op)

## E) route.request

1. Valid latency_sensitive request -> PASS
2. Missing requirements -> FAIL
3. Invalid workload_class -> FAIL
4. Deadline too low for policy -> PASS envelope / route.denied or IG FAIL

## F) component.fault

1. warn severity fault -> PASS
2. critical severity invariant trip -> PASS + expected quarantine command
3. Missing `code` -> FAIL

## G) component.quarantine

1. Quarantine with ttl and rejoin true -> PASS
2. ttl_sec = 0 -> FAIL
3. Missing `reason` -> FAIL

## H) ig.verdict

1. pass verdict with policy id -> PASS
2. fail verdict with rule hits -> PASS
3. invalid verdict value -> FAIL

---

## Lifecycle Transition Tests

1. Created -> Warmed (register success) -> PASS
2. Warmed -> Active (IG pass) -> PASS
3. Active -> Degraded (fault warn) -> PASS
4. Degraded -> Active (health recovery) -> PASS
5. Active -> Quarantined (critical fault + IG fail) -> PASS
6. Quarantined -> Warmed (ttl elapsed + IG pass) -> PASS
7. Any -> Retired (explicit teardown) -> PASS

---

## Replay / Audit Tests

1. All accepted messages written to append-only NDJSON -> PASS
2. Correlation chain reconstructs request->decision->result -> PASS
3. Replay reproduces route decision under same inputs -> PASS
4. Missing correlation id in log stream -> FAIL

---

## Exit Criteria (v1)

- 100% PASS on all envelope/schema tests.
- 100% expected behavior on lifecycle transitions.
- 100% correlation continuity in replay sample.
- IG fail path proven to trigger quarantine path.
