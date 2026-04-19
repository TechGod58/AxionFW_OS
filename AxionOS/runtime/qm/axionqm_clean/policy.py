from __future__ import annotations

from .estimator import RiskEstimate
from .profiles import PolicyProfile
from .types import CheckpointCandidate, DecisionRecord, TelemetryView


def rank_checkpoint_candidates(candidates: tuple[CheckpointCandidate, ...]) -> tuple[CheckpointCandidate, ...]:
    quality_rank = {"gold": 0, "silver": 1, "normal": 1, "transient": 2, "degraded": 3}
    return tuple(
        sorted(
            candidates,
            key=lambda item: (
                quality_rank.get(item.quality, 9),
                item.risk,
                -item.step,
            ),
        )
    )


def select_checkpoint(candidates: tuple[CheckpointCandidate, ...]) -> CheckpointCandidate | None:
    ranked = rank_checkpoint_candidates(candidates)
    return ranked[0] if ranked else None


def decide_action(
    view: TelemetryView,
    estimate: RiskEstimate,
    profile: PolicyProfile,
    allow_rollback: bool,
    recovering: bool,
) -> DecisionRecord:
    if estimate.risk >= profile.halt_threshold:
        return DecisionRecord(
            action="halt",
            reason="risk_exceeded_halt_threshold",
            risk=estimate.risk,
            level=estimate.level,
            recovery_state="irrecoverable",
        )
    if recovering and estimate.risk <= profile.recovered_threshold:
        return DecisionRecord(
            action="continue",
            reason="post_rollback_recovery_window",
            risk=estimate.risk,
            level=estimate.level,
            recovery_state="recovered",
        )
    if allow_rollback and estimate.risk >= profile.rollback_threshold:
        choice = select_checkpoint(view.runtime.checkpoint_candidates or view.checkpoint_candidates)
        if choice is not None:
            return DecisionRecord(
                action="rollback",
                rollback_to=choice.step,
                reason=f"rollback_to_{choice.quality}_checkpoint",
                risk=estimate.risk,
                level=estimate.level,
                recovery_state="recovering",
            )
    if (not view.runtime.checkpoint_available) and estimate.risk >= profile.checkpoint_threshold:
        return DecisionRecord(
            action="checkpoint",
            reason="risk_crossed_checkpoint_threshold",
            risk=estimate.risk,
            level=estimate.level,
            recovery_state="guarded",
        )
    return DecisionRecord(
        action="continue",
        reason="risk_within_operating_band",
        risk=estimate.risk,
        level=estimate.level,
        recovery_state="steady",
    )
