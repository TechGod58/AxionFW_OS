# VM Resource Policy v1

Goal: board-agnostic VM allocation with deterministic guardrails.

## 1) Allocation Inputs

- `resource_hints` from component register (`cpu`, `mem_mb`)
- workload class from `route.request`
- host telemetry snapshot (`cpu_used`, `mem_used_mb`, `io_load`)
- safety/risk state (IG/QM verdicts)

## 2) VM Classes

- `small`: 1 vCPU, 1024-2048 MB
- `medium`: 2 vCPU, 4096 MB
- `large`: 4 vCPU, 8192 MB

## 3) Workload Bias

- `latency_sensitive`: +CPU priority, low queue tolerance
- `stability_critical`: reserved headroom, anti-thrash policy
- `throughput_heavy`: batch queue, burst-limited

## 4) Guardrails

- host CPU ceiling: 80%
- host mem ceiling: 85%
- per-VM floor: 1 vCPU / 1024 MB
- deny/queue if request violates safety ceilings

## 5) Decision Outputs

- `ALLOCATE` with `{vcpu, mem_mb, priority}`
- `QUEUE` with reason and retry interval
- `DENY` with deterministic code
- `THROTTLE` for already-running VMs under stress

## 6) Determinism

Same input snapshot + same policy version => same allocation decision.
All decisions append to allocator audit log with `corr` id.

## 7) v1 Non-goals

- NUMA pinning
- GPU partitioning
- live migration
