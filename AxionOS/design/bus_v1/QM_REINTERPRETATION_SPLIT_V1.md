# QM Re-Interpretation Split v1

Purpose: map QM capabilities into the right execution layer so motherboard stays deterministic and OS stays adaptable.

## Layer Definitions

- **MoBo/Firmware Core**: deterministic, hardware-agnostic boot substrate.
- **OS Core Runtime**: always-on orchestration needed for normal operation.
- **OS Optional Modules**: advanced/adaptive modules loaded when needed.
- **Offboard/Batch**: heavy analytics, long stress runs, research tooling.

---

## Feature Split Table

| QM Capability / Area | Target Layer | Why |
|---|---|---|
| Device discovery handshake primitives | MoBo/Firmware Core | Must exist at boot, deterministic only |
| Basic capability enumeration (static) | MoBo/Firmware Core | Required for safe initial bring-up |
| Routing policy selection | OS Core Runtime | Adaptive decision belongs above firmware |
| Workload class handling (latency/stability/throughput) | OS Core Runtime | Runtime scheduling concern |
| Runtime hooks / lifecycle orchestration | OS Core Runtime | Dynamic component management |
| Invariant admission checks (IG integration point) | OS Core Runtime | Safety gate before execution admission |
| Continuous health monitoring | OS Core Runtime | Live operations concern |
| Fault-to-quarantine transitions | OS Core Runtime | Runtime safety and containment |
| Policy learning / bandit tuning | OS Optional Modules | Useful but not required for base run |
| Predictive controller / long horizon logic | OS Optional Modules | Advanced optimization path |
| Cross-run optimization sweeps | Offboard/Batch | Expensive and non-real-time |
| Massive phase matrix sweeps | Offboard/Batch | Research/provenance workload |
| Frontier analysis/report pack generation | Offboard/Batch | Analytics output, not execution path |
| Stress/chaos harnesses | Offboard/Batch | Validation tooling, not core path |
| CI gate aggregation and artifact export | Offboard/Batch | Build/release governance layer |

---

## Mandatory Rule Set

1. **No adaptive policy code in firmware layer.**
2. **No long-run analytics in OS core loop.**
3. **IG gate required at admission and fault escalation points.**
4. **QECC correction path exposed as capability, not hardcoded monolith.**
5. **Every route decision must be replayable via correlation ID.**

---

## Minimal OS-First Cut (implement now)

### Keep in OS Core now
- route.request / route.assigned handling
- component lifecycle FSM
- IG admission + quarantine hooks
- health heartbeat ingestion
- append-only audit NDJSON

### Defer to Optional/Offboard now
- bandit adaptation loops
- advanced predictive controllers
- multi-hour stress matrix orchestration
- report/plot/export pack generation

---

## QECC Positioning in This Split

- QECC should be a **runtime capability provider** (`qecc.decode`, `qecc.guard`, `qecc.repair_hint`) exposed over bus contract.
- OS Core invokes QECC through capability contracts.
- QECC sweeps/experiments stay offboard.

---

## Immediate Next Build Item

Create `AXIONOS_QM_ADAPTER_V1.md` defining:
- exact API shim surface from AxionOS to QM semantics
- supported message translations
- unsupported/deferred QM features
