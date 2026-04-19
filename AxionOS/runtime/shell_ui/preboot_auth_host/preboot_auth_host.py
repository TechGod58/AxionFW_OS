import json
import sys
from datetime import datetime, timezone
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


BUS = Path(axion_path_str("runtime", "shell_ui", "event_bus"))
if str(BUS) not in sys.path:
    sys.path.append(str(BUS))

from event_bus import publish

STATE_PATH = Path(axion_path_str("config", "PREBOOT_AUTH_STATE_V1.json"))
METHOD_MAP = {
    "password": "password",
    "pin": "pin",
    "recovery_key": "recovery_key",
    "security_key": "security_key",
    "biometric": "biometric",
    "fingerprint": "fingerprint",
    "face": "face_unlock",
    "face_unlock": "face_unlock",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load():
    return json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))


def _save(state):
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def snapshot(corr="corr_preboot_auth_001"):
    s = _load()
    out = {"ts": _now(), "corr": corr, **s}
    publish("shell.preboot_auth.refreshed", {"ok": True}, corr=corr, source="preboot_auth_host")
    return out


def choose_action(action: str, corr="corr_preboot_auth_action_001"):
    if action not in ("authenticate", "repair"):
        return {"ok": False, "code": "PREBOOT_AUTH_ACTION_UNKNOWN"}
    publish("shell.preboot_auth.action.selected", {"action": action}, corr=corr, source="preboot_auth_host")
    return {"ok": True, "code": "PREBOOT_AUTH_ACTION_OK", "action": action}


def set_method_availability(method: str, enabled: bool, corr="corr_preboot_auth_method_001"):
    mapped = METHOD_MAP.get(str(method or "").strip().lower())
    if not mapped:
        return {"ok": False, "code": "PREBOOT_AUTH_METHOD_UNKNOWN"}
    s = _load()
    methods = s.setdefault("methods", {})
    methods[mapped] = bool(enabled)
    if mapped in ("fingerprint", "face_unlock"):
        methods["biometric"] = bool(methods.get("fingerprint") or methods.get("face_unlock"))
    _save(s)
    out = {"ok": True, "code": "PREBOOT_AUTH_METHOD_SET_OK", "method": mapped, "enabled": bool(enabled)}
    publish("shell.preboot_auth.method.changed", out, corr=corr, source="preboot_auth_host")
    return out


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
