import sys
from pathlib import Path

_TOOLS_DIR = None
for _parent in Path(__file__).resolve().parents:
    if (_parent / "tools" / "common" / "pathing.py").exists():
        _TOOLS_DIR = _parent / "tools"
        break
if _TOOLS_DIR and str(_TOOLS_DIR) not in sys.path:
    sys.path.append(str(_TOOLS_DIR))

from common.pathing import axion_path


def axion_path_str(*parts):
    return str(axion_path(*parts))


import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

POLICY_PATH = Path(axion_path_str("config", "QM_ECC_POLICY_V1.json"))
STATE_PATH = Path(axion_path_str("config", "QM_ECC_STATE_V1.json"))
AUDIT_PATH = Path(axion_path_str("data", "audit", "qm_ecc_bridge.ndjson"))

_QM_CONTROLLER = None
_QM_IMPORT_ERROR = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _audit(event: dict[str, Any]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = dict(event)
    row.setdefault("ts", _now_iso())
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def load_policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        return {
            "version": 1,
            "policyId": "AXION_QM_ECC_POLICY_V1",
            "enabled": False,
            "deny_actions": ["rollback", "halt"],
            "checkpoint_actions": ["checkpoint"],
            "telemetry": {},
        }
    return _load_json(POLICY_PATH)


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {
            "version": 1,
            "policyId": "AXION_QM_ECC_STATE_V1",
            "decision_count": 0,
            "last_decision": None,
            "last_updated_utc": None,
        }
    return _load_json(STATE_PATH)


def save_state(state: dict[str, Any]) -> None:
    _save_json(STATE_PATH, state)


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _get_controller():
    global _QM_CONTROLLER, _QM_IMPORT_ERROR
    if _QM_CONTROLLER is not None:
        return _QM_CONTROLLER, None
    if _QM_IMPORT_ERROR is not None:
        return None, _QM_IMPORT_ERROR

    try:
        qm_root = Path(axion_path_str("runtime", "qm"))
        if str(qm_root) not in sys.path:
            sys.path.append(str(qm_root))
        from axionqm_clean.controller import QMController  # type: ignore

        _QM_CONTROLLER = QMController()
        return _QM_CONTROLLER, None
    except Exception as ex:
        _QM_IMPORT_ERROR = str(ex)
        return None, _QM_IMPORT_ERROR


def _signal_to_telemetry(signal: dict[str, Any], state: dict[str, Any], policy: dict[str, Any]):
    telemetry_cfg = dict(policy.get("telemetry") or {})
    step = _coerce_int(state.get("decision_count"), 0) + 1

    entropy = _coerce_float(signal.get("entropy", signal.get("qm_entropy", 0.0)), 0.0)
    error_rate = _coerce_float(signal.get("error_rate", signal.get("qm_error_rate", telemetry_cfg.get("default_error_rate", 0.02))), 0.02)
    instability = _coerce_float(signal.get("instability", signal.get("qm_instability", telemetry_cfg.get("default_instability", 0.01))), 0.01)

    force_action = str(signal.get("qm_force_action") or "").strip().lower()
    if force_action == "halt":
        error_rate = _coerce_float(telemetry_cfg.get("high_risk_error_rate", 0.8), 0.8)
        instability = _coerce_float(telemetry_cfg.get("high_risk_instability", 0.85), 0.85)
    elif force_action == "rollback":
        error_rate = max(error_rate, 0.62)
        instability = max(instability, 0.64)
    elif force_action == "checkpoint":
        error_rate = max(error_rate, 0.40)
        instability = max(instability, 0.36)

    metrics = {
        "entropy": entropy * _coerce_float(telemetry_cfg.get("entropy_weight", 1.0), 1.0),
        "error_rate": error_rate * _coerce_float(telemetry_cfg.get("error_rate_weight", 1.0), 1.0),
        "instability": instability * _coerce_float(telemetry_cfg.get("instability_weight", 1.0), 1.0),
        "runtime": {
            "last_action": (state.get("last_decision") or {}).get("action"),
            "rollback_count": _coerce_int(state.get("rollback_count", 0), 0),
            "last_rollback_step": (state.get("last_decision") or {}).get("step"),
            "checkpoint_available": bool(signal.get("checkpoint_available", True)),
            "checkpoint_candidates": list(signal.get("checkpoint_candidates") or []),
        },
    }
    return SimpleNamespace(step=step, metrics=metrics)


def evaluate_signal(signal: dict[str, Any], *, corr: str | None = None, domain: str = "runtime") -> dict[str, Any]:
    policy = load_policy()
    enabled = bool(policy.get("enabled", True))
    if not enabled:
        return {
            "ok": True,
            "code": "QM_ECC_DISABLED",
            "decision": {"action": "continue", "reason": "qm_disabled", "risk": 0.0, "level": "normal", "recovery_state": "steady"},
        }

    controller, err = _get_controller()
    if controller is None:
        return {
            "ok": False,
            "code": "QM_ECC_IMPORT_FAIL",
            "error": err,
            "decision": None,
        }

    state = load_state()
    telemetry = _signal_to_telemetry(dict(signal or {}), state, policy)
    decision = controller.evaluate(telemetry)
    action = str(getattr(decision, "action", "continue")).strip().lower() or "continue"
    force_action = str((signal or {}).get("qm_force_action") or "").strip().lower()
    forced = force_action in {"continue", "checkpoint", "rollback", "halt"}
    if forced:
        action = force_action

    deny_actions = {str(x).strip().lower() for x in policy.get("deny_actions", ["rollback", "halt"])}
    checkpoint_actions = {str(x).strip().lower() for x in policy.get("checkpoint_actions", ["checkpoint"])}

    state["decision_count"] = _coerce_int(state.get("decision_count"), 0) + 1
    if action == "rollback":
        state["rollback_count"] = _coerce_int(state.get("rollback_count"), 0) + 1
    state["last_decision"] = {
        "step": telemetry.step,
        "action": action,
        "reason": (f"forced_action:{force_action}" if forced else str(getattr(decision, "reason", ""))),
        "risk": _coerce_float(getattr(decision, "risk", 0.0), 0.0),
        "level": str(getattr(decision, "level", "normal")),
        "recovery_state": str(getattr(decision, "recovery_state", "steady")),
        "domain": str(domain),
    }
    state["last_updated_utc"] = _now_iso()
    save_state(state)

    out = {
        "ok": action not in deny_actions,
        "code": "QM_ECC_OK",
        "decision": state["last_decision"],
        "action": action,
        "is_checkpoint": action in checkpoint_actions,
        "denied": action in deny_actions,
        "contract_version": str(policy.get("contract_version", "axion.qm.v1")),
    }
    _audit(
        {
            "event": "qm_ecc.evaluate",
            "corr": corr,
            "domain": domain,
            "action": action,
            "ok": bool(out.get("ok")),
            "risk": state["last_decision"].get("risk"),
            "reason": state["last_decision"].get("reason"),
        }
    )
    return out


def evaluate_packet(packet: dict[str, Any], *, app_id: str | None = None, corr: str | None = None) -> dict[str, Any]:
    signal = dict(packet or {})
    signal.setdefault("entropy", _coerce_float(packet.get("entropy", 0.02), 0.02))
    signal.setdefault("error_rate", _coerce_float(packet.get("ecc_error_rate", packet.get("error_rate", 0.02)), 0.02))
    signal.setdefault("instability", _coerce_float(packet.get("instability", 0.01), 0.01))
    signal["app_id"] = str(app_id or packet.get("app_id") or "")
    return evaluate_signal(signal, corr=corr, domain="firewall")


def evaluate_runtime_launch(app_id: str, *, corr: str | None = None, compatibility: dict[str, Any] | None = None) -> dict[str, Any]:
    compat = dict(compatibility or {})
    signal = {
        "entropy": 0.02,
        "error_rate": 0.01,
        "instability": 0.01,
        "app_id": str(app_id),
        "family": str(compat.get("family", "")),
        "profile": str(compat.get("profile", "")),
        "execution_model": str(compat.get("execution_model", "")),
    }
    return evaluate_signal(signal, corr=corr, domain="runtime_launcher")


if __name__ == "__main__":
    print(json.dumps(evaluate_signal({"entropy": 0.1, "error_rate": 0.03, "instability": 0.02}), indent=2))
