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


BASE = Path(axion_path_str("runtime", "shell_ui", "event_bus"))
SECURITY_DIR = Path(axion_path_str("runtime", "security"))
if str(BASE) not in sys.path:
    sys.path.append(str(BASE))
if str(SECURITY_DIR) not in sys.path:
    sys.path.append(str(SECURITY_DIR))

from event_bus import publish
from os_encryption_guard import snapshot as os_encryption_snapshot, set_email_escrow as os_encryption_set_email_escrow, validate_pin

STATE_PATH = Path(axion_path_str("config", "ACCOUNTS_STATE_V1.json"))
ACCESS_PATH = Path(axion_path_str("config", "ACCESS_LEVELS_V1.json"))
PREBOOT_PATH = Path(axion_path_str("config", "PREBOOT_AUTH_STATE_V1.json"))

SIGNIN_METHOD_MAP = {
    "password": "password_enabled",
    "pin": "pin_enabled",
    "biometric": "biometric_enabled",
    "fingerprint": "fingerprint_enabled",
    "face": "face_unlock_enabled",
    "face_unlock": "face_unlock_enabled",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save(path, state):
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _ensure_signin_defaults(state: dict):
    signin = state.setdefault("signin", {})
    signin.setdefault("password_enabled", True)
    signin.setdefault("pin_enabled", True)
    signin.setdefault("biometric_enabled", False)
    signin.setdefault("fingerprint_enabled", False)
    signin.setdefault("face_unlock_enabled", False)
    signin.setdefault("mfa_enabled", False)
    signin.setdefault("pin_policy", {"min_length": 4, "max_length": 8, "digits_only": True})
    return signin


def _sync_preboot_method(method: str, enabled: bool):
    preboot = _load(PREBOOT_PATH)
    methods = preboot.setdefault("methods", {})
    if method in ("face", "face_unlock"):
        methods["face_unlock"] = bool(enabled)
    elif method in ("fingerprint",):
        methods["fingerprint"] = bool(enabled)
    elif method in ("biometric",):
        methods["biometric"] = bool(enabled)
    elif method in ("password", "pin"):
        methods[method] = bool(enabled)
    _save(PREBOOT_PATH, preboot)


def snapshot(corr="corr_accounts_snap_001"):
    s = _load(STATE_PATH)
    signin = _ensure_signin_defaults(s)
    access = _load(ACCESS_PATH)
    role = s.get("account", {}).get("role", "User")
    out = {
        "ts": _now(),
        "corr": corr,
        "account": s.get("account", {}),
        "signin": signin,
        "recovery": s.get("recovery", {}),
        "preboot_auth": _load(PREBOOT_PATH),
        "os_encryption": os_encryption_snapshot(include_policy=True),
        "access_level": access.get("levels", {}).get(role, {}),
        "users": s.get("users", []),
        "default_setup": s.get("default_setup", {}),
        "actions": [
            "update_profile",
            "toggle_signin_method",
            "set_pin",
            "set_password",
            "set_email_recovery_escrow",
            "generate_recovery_codes",
            "lock_session",
            "sign_out",
            "set_role",
            "enter_preboot_repair",
            "create_local_account",
        ],
    }
    publish("shell.accounts.refreshed", {"ok": True}, corr=corr, source="accounts_host")
    return out


def update_profile(display_name=None, handle=None, corr="corr_accounts_update_001"):
    s = _load(STATE_PATH)
    if display_name is not None:
        s["account"]["display_name"] = str(display_name)
    if handle is not None:
        s["account"]["handle"] = str(handle).lower()
    _save(STATE_PATH, s)
    publish(
        "shell.accounts.profile.updated",
        {"display_name": s["account"]["display_name"], "handle": s["account"]["handle"]},
        corr=corr,
        source="accounts_host",
    )
    return {"ok": True, "code": "ACCOUNTS_PROFILE_UPDATE_OK"}


def set_signin_method(method: str, enabled: bool, corr="corr_accounts_signin_001"):
    method_key = str(method or "").strip().lower()
    key = SIGNIN_METHOD_MAP.get(method_key)
    if not key:
        return {"ok": False, "code": "ACCOUNTS_SIGNIN_METHOD_UNKNOWN"}
    s = _load(STATE_PATH)
    signin = _ensure_signin_defaults(s)
    if key == "pin_enabled" and bool(enabled) and not bool(signin.get("pin_value_set", False)) and not bool(signin.get("pin_enabled", False)):
        return {"ok": False, "code": "ACCOUNTS_PIN_NOT_SET"}
    signin[key] = bool(enabled)
    if method_key in ("fingerprint", "face", "face_unlock"):
        signin["biometric_enabled"] = bool(signin.get("fingerprint_enabled") or signin.get("face_unlock_enabled"))
    _save(STATE_PATH, s)
    _sync_preboot_method(method_key, bool(enabled))
    if method_key in ("fingerprint", "face", "face_unlock"):
        _sync_preboot_method("biometric", bool(signin["biometric_enabled"]))
    publish(
        "shell.accounts.signin.changed",
        {"method": method_key, "enabled": bool(enabled)},
        corr=corr,
        source="accounts_host",
    )
    return {"ok": True, "code": "ACCOUNTS_SIGNIN_SET_OK", "method": method_key, "enabled": bool(enabled)}


def set_pin(pin: str, corr="corr_accounts_set_pin_001"):
    if not validate_pin(str(pin or "")):
        return {"ok": False, "code": "ACCOUNTS_PIN_INVALID"}
    s = _load(STATE_PATH)
    signin = _ensure_signin_defaults(s)
    signin["pin_value_set"] = True
    signin["pin_last_changed_utc"] = _now()
    signin["pin_enabled"] = True
    _save(STATE_PATH, s)
    _sync_preboot_method("pin", True)
    publish("shell.accounts.pin.changed", {"ok": True}, corr=corr, source="accounts_host")
    return {"ok": True, "code": "ACCOUNTS_PIN_SET_OK", "pin_length": len(str(pin))}


def set_password(password: str | None, corr="corr_accounts_set_password_001"):
    if password is not None and len(str(password)) < 8:
        return {"ok": False, "code": "ACCOUNTS_PASSWORD_TOO_SHORT"}
    s = _load(STATE_PATH)
    signin = _ensure_signin_defaults(s)
    signin["password_enabled"] = password is not None
    signin["password_last_changed_utc"] = _now() if password is not None else None
    _save(STATE_PATH, s)
    _sync_preboot_method("password", password is not None)
    publish(
        "shell.accounts.password.changed",
        {"enabled": password is not None},
        corr=corr,
        source="accounts_host",
    )
    return {"ok": True, "code": "ACCOUNTS_PASSWORD_SET_OK", "enabled": password is not None}


def set_email_recovery_escrow(address: str | None, enabled: bool, corr="corr_accounts_email_escrow_001"):
    out = os_encryption_set_email_escrow(address=address, enabled=bool(enabled), corr=corr)
    publish("shell.accounts.recovery.email_escrow.changed", out, corr=corr, source="accounts_host")
    return out


def set_role(role: str, corr="corr_accounts_role_001"):
    access = _load(ACCESS_PATH)
    if role not in access.get("levels", {}):
        return {"ok": False, "code": "ACCOUNTS_ROLE_UNKNOWN"}
    s = _load(STATE_PATH)
    s["account"]["role"] = role
    _save(STATE_PATH, s)
    publish("shell.accounts.role.changed", {"role": role}, corr=corr, source="accounts_host")
    return {"ok": True, "code": "ACCOUNTS_ROLE_SET_OK", "role": role}


def generate_recovery_codes(corr="corr_accounts_recovery_001"):
    s = _load(STATE_PATH)
    s.setdefault("recovery", {})["codes_generated"] = True
    s["recovery"]["last_generated"] = _now()
    _save(STATE_PATH, s)
    publish("shell.accounts.recovery.generated", {"ok": True}, corr=corr, source="accounts_host")
    return {"ok": True, "code": "ACCOUNTS_RECOVERY_CODES_OK"}


def session_action(action: str, corr="corr_accounts_session_001"):
    if action not in ("lock_session", "sign_out", "switch_user"):
        return {"ok": False, "code": "ACCOUNTS_SESSION_ACTION_UNKNOWN"}
    publish("shell.accounts.session.action", {"action": action}, corr=corr, source="accounts_host")
    return {"ok": True, "code": "ACCOUNTS_SESSION_ACTION_OK", "action": action}


def create_local_account(display_name: str, handle: str, role: str = "User", corr="corr_accounts_create_001"):
    access = _load(ACCESS_PATH)
    if role not in access.get("levels", {}):
        return {"ok": False, "code": "ACCOUNTS_ROLE_UNKNOWN"}
    s = _load(STATE_PATH)
    users = s.setdefault("users", [])
    lowered = str(handle).lower()
    if any(user.get("handle") == lowered for user in users):
        return {"ok": False, "code": "ACCOUNTS_HANDLE_EXISTS"}
    entry = {
        "user_id": f"usr_{len(users)+1:03d}",
        "display_name": str(display_name),
        "handle": lowered,
        "role": role,
        "bootstrap_admin": False,
        "default_profile_id": f"p{len(users)+1}",
        "created_utc": _now(),
    }
    users.append(entry)
    _save(STATE_PATH, s)
    publish("shell.accounts.user.created", entry, corr=corr, source="accounts_host")
    return {"ok": True, "code": "ACCOUNTS_USER_CREATE_OK", **entry}


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
