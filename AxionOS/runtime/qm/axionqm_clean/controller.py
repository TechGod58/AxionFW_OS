from __future__ import annotations

from .em_bridge import AxionEMBridge
from .estimator import estimate_risk
from .policy import decide_action
from .profiles import get_profile
from .settings import QMSettings
from .types import DecisionRecord, telemetry_from_engine


class QMController:
    def __init__(self, settings: QMSettings | None = None) -> None:
        self.settings = settings or QMSettings.load()
        self.profile = get_profile(self.settings.profile)
        self.bridge = AxionEMBridge(
            enabled=self.settings.em_enabled,
            em_root=self.settings.em_root,
            config_path=self.settings.em_config_path,
        )
        self._last_rollback_step: int | None = None

    def evaluate(self, telemetry) -> DecisionRecord:
        view = telemetry_from_engine(telemetry)
        advisory = self.bridge.advise(view)
        estimate = estimate_risk(view, advisory_bias=advisory.bias)
        recovering = (
            self._last_rollback_step is not None
            and (view.step - self._last_rollback_step) <= self.settings.recovery_window_steps
        )
        cooldown_active = (
            self._last_rollback_step is not None
            and (view.step - self._last_rollback_step) <= self.settings.rollback_cooldown_steps
        )
        decision = decide_action(
            view=view,
            estimate=estimate,
            profile=self.profile,
            allow_rollback=not cooldown_active,
            recovering=recovering,
        )
        if decision.action == "rollback":
            self._last_rollback_step = view.step
        return decision
