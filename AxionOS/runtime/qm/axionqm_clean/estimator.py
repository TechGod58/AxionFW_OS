from __future__ import annotations

from dataclasses import dataclass

from .types import TelemetryView


@dataclass(frozen=True)
class RiskEstimate:
    risk: float
    level: str


def estimate_risk(view: TelemetryView, advisory_bias: float = 0.0) -> RiskEstimate:
    raw = (
        0.45 * max(view.entropy, 0.0)
        + 0.35 * max(view.error_rate, 0.0)
        + 0.20 * max(view.instability, 0.0)
        + advisory_bias
    )
    risk = max(0.0, min(1.0, raw))
    if risk < 0.25:
        level = "normal"
    elif risk < 0.50:
        level = "elevated"
    elif risk < 0.75:
        level = "critical"
    else:
        level = "terminal"
    return RiskEstimate(risk=risk, level=level)
