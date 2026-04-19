# Engine QM Contract

Contract version: `axion.qm.v1`

## Engine Telemetry

- `step`
- `metrics.entropy`
- `metrics.error_rate`
- `metrics.instability`
- `metrics.runtime.last_action`
- `metrics.runtime.rollback_count`
- `metrics.runtime.last_rollback_step`
- `metrics.runtime.checkpoint_available`
- `metrics.runtime.checkpoint_candidates[]`

## QM Decisions

- `action`: `continue` | `checkpoint` | `rollback` | `halt`
- `rollback_to`
- `reason`
- `risk`
- `level`
- `recovery_state`
- `contract_version`
