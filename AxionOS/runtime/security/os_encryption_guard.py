from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AXION_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = AXION_ROOT / "config" / "OS_ENCRYPTION_STATE_V1.json"
RECOVERY_DIR = AXION_ROOT / "data" / "security" / "recovery"
AUDIT_PATH = AXION_ROOT / "data" / "audit" / "os_encryption_guard.ndjson"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> dict[str, Any]:
    return {
        "version": 1,
        "policy": {
            "enabled": False,
            "algorithm": "aes-256-gcm",
            "scope": ["os_volume", "profile_storage"],
            "requires_preboot_auth": False,
            "key_prompt_mode": "external_offline_access_only",
            "allow_email_recovery_escrow": False,
        },
        "runtime": {
            "status": "not_configured",
            "last_updated_utc": None,
            "last_key_rotation_utc": None,
            "normal_boot_unlock_mode": "transparent_via_trusted_boot",
        },
        "recovery": {
            "key_id": None,
            "key_hint": None,
            "local_secure_path": None,
            "email_escrow": {
                "enabled": False,
                "address": None,
                "delivery_mode": "manual_out_of_band_only",
                "last_staged_utc": None,
            },
        },
        "setup_requirements": {
            "computer_name_required": True,
            "username_required": True,
            "password_optional": True,
            "pin_length": {"min": 4, "max": 8},
            "biometric": {"fingerprint_supported": True, "face_unlock_supported": True},
        },
    }


def _audit(event: dict[str, Any]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = dict(event)
    row.setdefault("ts", _now_iso())
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return _default_state()
    try:
        obj = json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return _default_state()
    if not isinstance(obj, dict):
        return _default_state()
    base = _default_state()
    for key in ("policy", "runtime", "recovery", "setup_requirements"):
        if not isinstance(obj.get(key), dict):
            obj[key] = dict(base[key])
    if not isinstance((obj.get("recovery") or {}).get("email_escrow"), dict):
        obj["recovery"]["email_escrow"] = dict(base["recovery"]["email_escrow"])
    return obj


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _validate_computer_name(name: str) -> bool:
    text = str(name or "").strip()
    if not text or len(text) > 15:
        return False
    return re.match(r"^[A-Za-z0-9][A-Za-z0-9\-]{0,13}[A-Za-z0-9]$", text) is not None or len(text) == 1


def _validate_email(email: str | None) -> bool:
    text = str(email or "").strip()
    if not text:
        return False
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", text) is not None


def validate_pin(pin: str | None, *, min_len: int = 4, max_len: int = 8) -> bool:
    if pin is None:
        return True
    value = str(pin).strip()
    if not value.isdigit():
        return False
    return min_len <= len(value) <= max_len


def _generate_recovery_key() -> str:
    return "-".join(secrets.token_hex(2).upper() for _ in range(8))


def _write_recovery_package(
    *,
    key_id: str,
    recovery_key: str,
    computer_name: str,
    user_name: str,
    user_handle: str,
    corr: str | None,
) -> Path:
    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
    path = RECOVERY_DIR / f"{key_id}.json"
    pkg = {
        "version": 1,
        "key_id": key_id,
        "recovery_key": recovery_key,
        "computer_name": computer_name,
        "user_name": user_name,
        "user_handle": user_handle,
        "created_utc": _now_iso(),
        "corr": corr,
    }
    path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")
    return path


def snapshot(*, include_policy: bool = True) -> dict[str, Any]:
    state = _load_state()
    out = {
        "ok": True,
        "code": "OS_ENCRYPTION_STATUS_OK",
        "version": state.get("version", 1),
        "runtime": dict(state.get("runtime") or {}),
        "recovery": {
            "key_id": (state.get("recovery") or {}).get("key_id"),
            "key_hint": (state.get("recovery") or {}).get("key_hint"),
            "local_secure_path": (state.get("recovery") or {}).get("local_secure_path"),
            "email_escrow": dict(((state.get("recovery") or {}).get("email_escrow") or {})),
        },
        "setup_requirements": dict(state.get("setup_requirements") or {}),
    }
    if include_policy:
        out["policy"] = dict(state.get("policy") or {})
    return out


def key_required_for_context(access_context: str) -> dict[str, Any]:
    mode = str(access_context or "").strip().lower()
    if mode in ("external_disk_mount", "offline_forensics", "raw_block_access"):
        return {"ok": True, "required": True, "code": "OS_ENCRYPTION_KEY_REQUIRED_EXTERNAL"}
    return {"ok": True, "required": False, "code": "OS_ENCRYPTION_KEY_NOT_REQUIRED_NORMAL_BOOT"}


def set_email_escrow(address: str | None, enabled: bool, *, corr: str | None = None) -> dict[str, Any]:
    state = _load_state()
    escrow = state.setdefault("recovery", {}).setdefault("email_escrow", {})
    if enabled and not _validate_email(address):
        return {"ok": False, "code": "OS_ENCRYPTION_EMAIL_INVALID"}
    if enabled and not bool(state.setdefault("policy", {}).get("allow_email_recovery_escrow", False)):
        return {"ok": False, "code": "OS_ENCRYPTION_EMAIL_ESCROW_DISABLED_BY_POLICY"}
    escrow["enabled"] = bool(enabled)
    escrow["address"] = str(address or "").strip() or None
    escrow["last_staged_utc"] = _now_iso() if enabled else None
    state.setdefault("runtime", {})["last_updated_utc"] = _now_iso()
    _save_state(state)
    out = {
        "ok": True,
        "code": "OS_ENCRYPTION_EMAIL_ESCROW_SET",
        "enabled": bool(enabled),
        "address": escrow.get("address"),
        "warning": (
            "Email escrow is staged for manual out-of-band delivery only."
            if enabled
            else None
        ),
    }
    _audit(
        {
            "event": "os.encryption.email_escrow.set",
            "ok": True,
            "enabled": bool(enabled),
            "address": escrow.get("address"),
            "corr": corr,
        }
    )
    return out


def provision(
    *,
    computer_name: str,
    user_name: str,
    user_handle: str,
    password: str | None = None,
    pin: str | None = None,
    enable_fingerprint: bool = False,
    enable_face_unlock: bool = False,
    recovery_email: str | None = None,
    allow_email_escrow: bool = False,
    corr: str | None = None,
) -> dict[str, Any]:
    if not _validate_computer_name(computer_name):
        return {"ok": False, "code": "OS_ENCRYPTION_COMPUTER_NAME_INVALID"}
    if not str(user_name or "").strip():
        return {"ok": False, "code": "OS_ENCRYPTION_USER_NAME_REQUIRED"}
    if not str(user_handle or "").strip():
        return {"ok": False, "code": "OS_ENCRYPTION_USER_HANDLE_REQUIRED"}
    if password is not None and len(str(password)) < 8:
        return {"ok": False, "code": "OS_ENCRYPTION_PASSWORD_TOO_SHORT"}
    if not validate_pin(pin):
        return {"ok": False, "code": "OS_ENCRYPTION_PIN_INVALID"}
    if allow_email_escrow and not _validate_email(recovery_email):
        return {"ok": False, "code": "OS_ENCRYPTION_EMAIL_INVALID"}

    state = _load_state()
    state.setdefault("policy", {})["enabled"] = True
    state["policy"]["requires_preboot_auth"] = False
    state["policy"]["key_prompt_mode"] = "external_offline_access_only"
    state["policy"]["allow_email_recovery_escrow"] = bool(allow_email_escrow)
    state.setdefault("runtime", {})["status"] = "active"
    state["runtime"]["last_updated_utc"] = _now_iso()
    state["runtime"]["normal_boot_unlock_mode"] = "transparent_via_trusted_boot"
    key_id = f"rk_{secrets.token_hex(6)}"
    recovery_key = _generate_recovery_key()
    pkg_path = _write_recovery_package(
        key_id=key_id,
        recovery_key=recovery_key,
        computer_name=str(computer_name).strip(),
        user_name=str(user_name).strip(),
        user_handle=str(user_handle).strip().lower(),
        corr=corr,
    )

    state.setdefault("recovery", {})["key_id"] = key_id
    state["recovery"]["key_hint"] = recovery_key[-4:]
    state["recovery"]["local_secure_path"] = str(pkg_path)
    escrow = state["recovery"].setdefault("email_escrow", {})
    escrow["enabled"] = bool(allow_email_escrow and _validate_email(recovery_email))
    escrow["address"] = str(recovery_email or "").strip() or None
    escrow["last_staged_utc"] = _now_iso() if escrow.get("enabled") else None
    _save_state(state)

    out = {
        "ok": True,
        "code": "OS_ENCRYPTION_PROVISIONED",
        "policy_enabled": True,
        "status": "active",
        "key_prompt_mode": state["policy"]["key_prompt_mode"],
        "normal_boot_unlock_mode": state["runtime"]["normal_boot_unlock_mode"],
        "recovery_key_id": key_id,
        "recovery_key": recovery_key,
        "recovery_package_path": str(pkg_path),
        "email_escrow_enabled": bool(escrow.get("enabled")),
        "email_escrow_warning": (
            "Recovery email delivery is staged only; send out-of-band manually."
            if escrow.get("enabled")
            else None
        ),
        "signin": {
            "password_enabled": password is not None,
            "pin_enabled": pin is not None,
            "fingerprint_enabled": bool(enable_fingerprint),
            "face_unlock_enabled": bool(enable_face_unlock),
        },
    }
    _audit(
        {
            "event": "os.encryption.provision",
            "ok": True,
            "computer_name": str(computer_name).strip(),
            "user_handle": str(user_handle).strip().lower(),
            "email_escrow_enabled": bool(escrow.get("enabled")),
            "corr": corr,
        }
    )
    return out


def rotate_recovery_key(
    *,
    corr: str | None = None,
    reason: str = "manual_rotation",
) -> dict[str, Any]:
    state = _load_state()
    if not bool((state.get("policy") or {}).get("enabled")):
        return {"ok": False, "code": "OS_ENCRYPTION_NOT_ENABLED"}
    previous_key_id = str((state.get("recovery") or {}).get("key_id") or "")
    new_key_id = f"rk_{secrets.token_hex(6)}"
    recovery_key = _generate_recovery_key()

    pkg_path = _write_recovery_package(
        key_id=new_key_id,
        recovery_key=recovery_key,
        computer_name="unknown",
        user_name="unknown",
        user_handle="unknown",
        corr=corr,
    )
    state.setdefault("recovery", {})["key_id"] = new_key_id
    state["recovery"]["key_hint"] = recovery_key[-4:]
    state["recovery"]["local_secure_path"] = str(pkg_path)
    state.setdefault("runtime", {})["last_key_rotation_utc"] = _now_iso()
    state["runtime"]["last_updated_utc"] = _now_iso()
    _save_state(state)

    out = {
        "ok": True,
        "code": "OS_ENCRYPTION_RECOVERY_KEY_ROTATED",
        "previous_key_id": previous_key_id or None,
        "recovery_key_id": new_key_id,
        "recovery_key": recovery_key,
        "recovery_package_path": str(pkg_path),
        "reason": str(reason or "manual_rotation"),
    }
    _audit(
        {
            "event": "os.encryption.recovery_key.rotate",
            "ok": True,
            "previous_key_id": previous_key_id or None,
            "new_key_id": new_key_id,
            "reason": str(reason or "manual_rotation"),
            "corr": corr,
        }
    )
    return out
