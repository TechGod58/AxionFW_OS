from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_TOOLS_DIR = None
for _parent in Path(__file__).resolve().parents:
    if (_parent / "tools" / "common" / "pathing.py").exists():
        _TOOLS_DIR = _parent / "tools"
        break
if _TOOLS_DIR and str(_TOOLS_DIR) not in sys.path:
    sys.path.append(str(_TOOLS_DIR))

from common.pathing import axion_path


OS_ROOT = axion_path()
WORKSPACE_ROOT = OS_ROOT.parent
FW_BASE = WORKSPACE_ROOT / "AxionFW" / "Base"
POLICY_PATH = axion_path("config", "BIOS_SETTINGS_POLICY_V1.json")
PENDING_PATH = FW_BASE / "out" / "handoff" / "pending_bios_settings_v1.json"
AUDIT_PATH = axion_path("out", "runtime", "bios_settings_staging_audit.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _validate_single_setting(key: str, value: Any, spec: dict[str, Any]) -> tuple[bool, Any, str | None]:
    stype = str(spec.get("type") or "").strip().lower()
    if stype == "bool":
        if isinstance(value, bool):
            return True, value, None
        return False, None, f"{key} must be bool"
    if stype == "int":
        if not isinstance(value, int):
            return False, None, f"{key} must be int"
        if "min" in spec and value < int(spec["min"]):
            return False, None, f"{key} must be >= {int(spec['min'])}"
        if "max" in spec and value > int(spec["max"]):
            return False, None, f"{key} must be <= {int(spec['max'])}"
        return True, value, None
    if stype == "enum":
        allowed = [str(x) for x in (spec.get("allowed") or [])]
        sval = str(value)
        if sval not in allowed:
            return False, None, f"{key} must be one of {allowed}"
        return True, sval, None
    if stype == "string":
        if isinstance(value, str) and value.strip():
            return True, value.strip(), None
        return False, None, f"{key} must be non-empty string"
    return False, None, f"{key} has unsupported type policy: {stype}"


def _validate_settings(settings: dict[str, Any], policy: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    allowed = dict(policy.get("allowedSettings") or {})
    forbidden = {str(x).strip().lower() for x in (policy.get("forbiddenSettings") or [])}
    normalized: dict[str, Any] = {}
    errors: list[str] = []

    for key, value in settings.items():
        k = str(key).strip()
        if not k:
            errors.append("empty setting key is not allowed")
            continue
        if k.lower() in forbidden:
            errors.append(f"{k} is forbidden by policy")
            continue
        spec = allowed.get(k)
        if not isinstance(spec, dict):
            errors.append(f"{k} is not allowlisted")
            continue
        ok, norm_value, err = _validate_single_setting(k, value, spec)
        if not ok:
            errors.append(str(err))
            continue
        normalized[k] = norm_value

    if not normalized and not errors:
        errors.append("no settings provided")
    return normalized, errors


def get_pending_bios_settings() -> dict[str, Any]:
    pending = _load_json(PENDING_PATH, None)
    if not isinstance(pending, dict) or not pending:
        return {
            "ok": True,
            "code": "BIOS_SETTINGS_NONE_PENDING",
            "pending_path": str(PENDING_PATH),
            "pending": None,
            "restart_required": False,
        }
    return {
        "ok": True,
        "code": "BIOS_SETTINGS_PENDING_FOUND",
        "pending_path": str(PENDING_PATH),
        "pending": pending,
        "restart_required": bool(pending.get("apply_after_restart", True)),
    }


def stage_bios_settings(
    settings: dict[str, Any],
    *,
    actor: str = "os_user",
    corr: str | None = None,
) -> dict[str, Any]:
    policy = _load_json(POLICY_PATH, {})
    if not isinstance(policy, dict) or not policy:
        return {
            "ok": False,
            "code": "BIOS_SETTINGS_POLICY_MISSING",
            "policy_path": str(POLICY_PATH),
        }

    if not isinstance(settings, dict):
        return {
            "ok": False,
            "code": "BIOS_SETTINGS_INVALID_PAYLOAD",
            "detail": "settings must be an object",
        }

    normalized, errors = _validate_settings(settings, policy)
    if errors:
        out = {
            "ok": False,
            "code": "BIOS_SETTINGS_VALIDATION_FAIL",
            "policy_path": str(POLICY_PATH),
            "errors": errors,
        }
        _write_json(
            AUDIT_PATH,
            {
                "timestamp_utc": _now_iso(),
                "status": "FAIL",
                "code": out["code"],
                "errors": errors,
                "actor": actor,
                "corr": corr or "",
            },
        )
        return out

    existing = _load_json(PENDING_PATH, {})
    prior_revision = int(existing.get("revision", 0)) if isinstance(existing, dict) else 0
    request = {
        "version": 1,
        "contract_id": "AXION_BIOS_SETTINGS_STAGE_V1",
        "policy_id": str(policy.get("policyId") or "AXION_BIOS_SETTINGS_POLICY_V1"),
        "requested_utc": _now_iso(),
        "request_id": f"bios_stage_{uuid.uuid4().hex}",
        "revision": prior_revision + 1,
        "actor": str(actor or "os_user"),
        "corr": str(corr or ""),
        "status": "PENDING_RESTART",
        "apply_after_restart": True,
        "restart_required": True,
        "settings": normalized,
        "source": "AxionOS/runtime/firmware/bios_settings_bridge.py",
    }

    _write_json(PENDING_PATH, request)
    _write_json(
        AUDIT_PATH,
        {
            "timestamp_utc": _now_iso(),
            "status": "PASS",
            "code": "BIOS_SETTINGS_STAGED_PENDING_RESTART",
            "pending_path": str(PENDING_PATH),
            "request_id": request["request_id"],
            "revision": request["revision"],
            "settings_keys": sorted(normalized.keys()),
            "actor": actor,
            "corr": corr or "",
        },
    )
    return {
        "ok": True,
        "code": "BIOS_SETTINGS_STAGED_PENDING_RESTART",
        "pending_path": str(PENDING_PATH),
        "request_id": request["request_id"],
        "revision": request["revision"],
        "restart_required": True,
        "pending": request,
    }

