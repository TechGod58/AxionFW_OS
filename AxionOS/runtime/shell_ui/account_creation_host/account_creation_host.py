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
SECURITY_DIR = Path(axion_path_str("runtime", "security"))
if str(BUS) not in sys.path:
    sys.path.append(str(BUS))
if str(SECURITY_DIR) not in sys.path:
    sys.path.append(str(SECURITY_DIR))

from event_bus import publish
from os_encryption_guard import provision as provision_os_encryption, validate_pin

STATE_PATH = Path(axion_path_str("config", "ACCOUNT_CREATION_STATE_V1.json"))
ACCOUNTS_PATH = Path(axion_path_str("config", "ACCOUNTS_STATE_V1.json"))
INSTALL_IDENTITY_PATH = Path(axion_path_str("config", "INSTALL_IDENTITY_V1.json"))
PREBOOT_PATH = Path(axion_path_str("config", "PREBOOT_AUTH_STATE_V1.json"))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save(path, state):
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _find_user(users, handle: str):
    lowered = str(handle).lower()
    for user in users:
        if str(user.get("handle", "")).lower() == lowered:
            return user
    return None


def _upsert_user(accounts_state: dict, display_name: str, handle: str, role: str):
    users = accounts_state.setdefault("users", [])
    lowered = str(handle).lower()
    existing = _find_user(users, lowered)
    if existing is None:
        existing = {
            "user_id": f"usr_{len(users)+1:03d}",
            "display_name": str(display_name),
            "handle": lowered,
            "role": role,
            "bootstrap_admin": role == "Administrator",
            "default_profile_id": f"p{len(users)+1}",
            "created_utc": _now(),
        }
        users.append(existing)
    else:
        existing["display_name"] = str(display_name)
        existing["role"] = role
    return existing


def snapshot(corr="corr_account_creation_001"):
    state = _load(STATE_PATH)
    accounts = _load(ACCOUNTS_PATH)
    out = {"ts": _now(), "corr": corr, **state, "accounts_count": len(accounts.get("users", []))}
    publish("shell.account_creation.refreshed", {"ok": True}, corr=corr, source="account_creation_host")
    return out


def create_account(display_name: str, handle: str, role: str = "User", corr="corr_account_create_001"):
    state = _load(STATE_PATH)
    if role not in state.get("allowed_roles", []):
        return {"ok": False, "code": "ACCOUNT_CREATION_ROLE_UNKNOWN"}
    accounts = _load(ACCOUNTS_PATH)
    users = accounts.setdefault("users", [])
    lowered = str(handle).lower()
    if any(user.get("handle") == lowered for user in users):
        return {"ok": False, "code": "ACCOUNT_CREATION_HANDLE_EXISTS"}
    user_id = f"usr_{len(users)+1:03d}"
    profile_id = f"p{len(users)+1}"
    entry = {
        "user_id": user_id,
        "display_name": str(display_name),
        "handle": lowered,
        "role": role,
        "bootstrap_admin": False,
        "default_profile_id": profile_id,
        "created_utc": _now(),
    }
    users.append(entry)
    _save(ACCOUNTS_PATH, accounts)
    publish("shell.account_creation.created", entry, corr=corr, source="account_creation_host")
    return {"ok": True, "code": "ACCOUNT_CREATION_OK", **entry}


def run_setup_wizard(
    computer_name: str,
    display_name: str,
    handle: str,
    role: str = "Administrator",
    password: str | None = None,
    pin: str | None = None,
    enable_fingerprint: bool = False,
    enable_face_unlock: bool = False,
    recovery_email: str | None = None,
    allow_email_escrow: bool = False,
    corr="corr_account_setup_wizard_001",
):
    state = _load(STATE_PATH)
    if role not in state.get("allowed_roles", []):
        return {"ok": False, "code": "ACCOUNT_CREATION_ROLE_UNKNOWN"}
    if not str(computer_name or "").strip():
        return {"ok": False, "code": "ACCOUNT_CREATION_COMPUTER_NAME_REQUIRED"}
    if not str(display_name or "").strip():
        return {"ok": False, "code": "ACCOUNT_CREATION_DISPLAY_NAME_REQUIRED"}
    lowered_handle = str(handle or "").strip().lower()
    if not lowered_handle:
        return {"ok": False, "code": "ACCOUNT_CREATION_HANDLE_REQUIRED"}
    if password is not None and len(str(password)) < 8:
        return {"ok": False, "code": "ACCOUNT_CREATION_PASSWORD_TOO_SHORT"}
    if pin is not None and not validate_pin(str(pin)):
        return {"ok": False, "code": "ACCOUNT_CREATION_PIN_INVALID"}

    accounts = _load(ACCOUNTS_PATH)
    user = _upsert_user(accounts, display_name=display_name, handle=lowered_handle, role=role)
    accounts["account"] = {
        "user_id": user.get("user_id"),
        "display_name": str(display_name),
        "handle": lowered_handle,
        "role": role,
        "avatar": accounts.get("account", {}).get("avatar"),
    }
    signin = accounts.setdefault("signin", {})
    signin["password_enabled"] = password is not None
    signin["pin_enabled"] = pin is not None
    signin["biometric_enabled"] = bool(enable_fingerprint or enable_face_unlock)
    signin["fingerprint_enabled"] = bool(enable_fingerprint)
    signin["face_unlock_enabled"] = bool(enable_face_unlock)
    signin.setdefault("mfa_enabled", False)
    signin.setdefault("pin_policy", {"min_length": 4, "max_length": 8, "digits_only": True})
    accounts.setdefault("default_setup", {})["last_setup_completed_utc"] = _now()
    accounts["default_setup"]["password_optional"] = True
    accounts["default_setup"]["pin_length"] = {"min": 4, "max": 8}
    _save(ACCOUNTS_PATH, accounts)

    install = _load(INSTALL_IDENTITY_PATH)
    install.setdefault("install", {})["computer_name"] = str(computer_name).strip()
    install["install"]["owner"] = str(display_name).strip()
    _save(INSTALL_IDENTITY_PATH, install)

    preboot = _load(PREBOOT_PATH)
    methods = preboot.setdefault("methods", {})
    methods["password"] = password is not None
    methods["pin"] = pin is not None
    methods["fingerprint"] = bool(enable_fingerprint)
    methods["face_unlock"] = bool(enable_face_unlock)
    methods["biometric"] = bool(enable_fingerprint or enable_face_unlock)
    _save(PREBOOT_PATH, preboot)

    enc = provision_os_encryption(
        computer_name=str(computer_name).strip(),
        user_name=str(display_name).strip(),
        user_handle=lowered_handle,
        password=password,
        pin=str(pin) if pin is not None else None,
        enable_fingerprint=bool(enable_fingerprint),
        enable_face_unlock=bool(enable_face_unlock),
        recovery_email=recovery_email,
        allow_email_escrow=bool(allow_email_escrow),
        corr=corr,
    )
    if not bool(enc.get("ok")):
        return {"ok": False, "code": "ACCOUNT_CREATION_ENCRYPTION_FAIL", "encryption": enc}

    out = {
        "ok": True,
        "code": "ACCOUNT_SETUP_WIZARD_OK",
        "computer_name": install["install"]["computer_name"],
        "account": accounts["account"],
        "signin": signin,
        "preboot_methods": methods,
        "encryption": {
            "code": enc.get("code"),
            "recovery_key_id": enc.get("recovery_key_id"),
            "recovery_key": enc.get("recovery_key"),
            "recovery_package_path": enc.get("recovery_package_path"),
            "email_escrow_enabled": enc.get("email_escrow_enabled"),
            "email_escrow_warning": enc.get("email_escrow_warning"),
        },
    }
    publish("shell.account_creation.setup.completed", out, corr=corr, source="account_creation_host")
    return out


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
