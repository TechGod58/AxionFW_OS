from __future__ import annotations

from .controller import QMController

try:
    from axione.plugins.qm_abi import Decision, QMPlugin
except Exception:  # pragma: no cover
    class QMPlugin:  # type: ignore[override]
        pass

    class Decision:  # pragma: no cover
        def __init__(
            self,
            action: str,
            rollback_to: int | None = None,
            reason: str = "",
            risk: float = 0.0,
            level: str = "normal",
            recovery_state: str = "steady",
            contract_version: str = "axion.qm.v1",
            profile_mode: str = "balanced",
        ) -> None:
            self.action = action
            self.rollback_to = rollback_to
            self.reason = reason
            self.risk = risk
            self.level = level
            self.recovery_state = recovery_state
            self.contract_version = contract_version
            self.profile_mode = profile_mode


class QM(QMPlugin):
    def __init__(self) -> None:
        self.controller = QMController()

    def on_step(self, telemetry):
        result = self.controller.evaluate(telemetry)
        return Decision(
            action=result.action,
            rollback_to=result.rollback_to,
            reason=result.reason,
            risk=result.risk,
            level=result.level,
            recovery_state=result.recovery_state,
            contract_version="axion.qm.v1",
            profile_mode=self.controller.profile.name,
        )
