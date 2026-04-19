from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckpointCandidate:
    checkpoint_id: str
    step: int
    quality: str
    risk: float
    level: str


@dataclass(frozen=True)
class RuntimeState:
    last_action: str | None
    rollback_count: int
    last_rollback_step: int | None
    checkpoint_available: bool
    checkpoint_candidates: tuple[CheckpointCandidate, ...]


@dataclass(frozen=True)
class TelemetryView:
    step: int
    entropy: float
    error_rate: float
    instability: float
    checkpoint_candidates: tuple[CheckpointCandidate, ...]
    runtime: RuntimeState


@dataclass(frozen=True)
class DecisionRecord:
    action: str
    rollback_to: int | None = None
    reason: str = ""
    risk: float = 0.0
    level: str = "normal"
    recovery_state: str = "steady"


def _candidate_from_row(index: int, row: dict) -> CheckpointCandidate:
    return CheckpointCandidate(
        checkpoint_id=str(row.get("checkpoint_id", f"checkpoint-{index}")),
        step=int(row.get("step", 0)),
        quality=str(row.get("quality", "transient")),
        risk=float(row.get("risk", 1.0)),
        level=str(row.get("level", "degraded")),
    )


def telemetry_from_engine(telemetry) -> TelemetryView:
    metrics = dict(getattr(telemetry, "metrics", {}) or {})
    runtime_metrics = dict(metrics.get("runtime", {}) or {})
    checkpoint_rows = tuple(
        _candidate_from_row(index, row)
        for index, row in enumerate(runtime_metrics.get("checkpoint_candidates", []) or ())
    )
    return TelemetryView(
        step=int(getattr(telemetry, "step", 0)),
        entropy=float(metrics.get("entropy", 0.0)),
        error_rate=float(metrics.get("error_rate", metrics.get("decoherence", 0.0))),
        instability=float(metrics.get("instability", metrics.get("leakage", 0.0))),
        checkpoint_candidates=checkpoint_rows,
        runtime=RuntimeState(
            last_action=runtime_metrics.get("last_action"),
            rollback_count=int(runtime_metrics.get("rollback_count", 0)),
            last_rollback_step=runtime_metrics.get("last_rollback_step"),
            checkpoint_available=bool(
                runtime_metrics.get("checkpoint_available", bool(checkpoint_rows))
            ),
            checkpoint_candidates=checkpoint_rows,
        ),
    )
