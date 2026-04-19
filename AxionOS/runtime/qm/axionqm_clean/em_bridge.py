from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .types import TelemetryView


@dataclass(frozen=True)
class EMBias:
    bias: float
    status: str


class AxionEMBridge:
    def __init__(self, enabled: bool, em_root: Path | None, config_path: Path | None) -> None:
        self.enabled = enabled
        self.em_root = em_root
        self.config_path = config_path

    def advise(self, telemetry: TelemetryView) -> EMBias:
        if not self.enabled:
            return EMBias(bias=0.0, status="disabled")
        if self.config_path is None or not self.config_path.exists():
            return EMBias(bias=0.0, status="missing_config")
        payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        weight = float(payload.get("risk_bias_weight", 0.0))
        return EMBias(
            bias=max(0.0, min(0.2, telemetry.instability * weight)),
            status="ok",
        )
