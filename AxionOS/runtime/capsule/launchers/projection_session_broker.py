from __future__ import annotations

import json
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AXION_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = AXION_ROOT / "config" / "SANDBOX_PROJECTION_POLICY_V1.json"
SESSION_REGISTRY_PATH = AXION_ROOT / "config" / "SANDBOX_PROJECTION_SESSION_REGISTRY_V1.json"
AUDIT_PATH = AXION_ROOT / "data" / "audit" / "projection_sessions.ndjson"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _default_policy() -> dict[str, Any]:
    return {
        "version": 1,
        "policyId": "AXION_SANDBOX_PROJECTION_POLICY_V1",
        "session": {
            "session_root": "data/rootfs/Sandbox Projections/Sessions",
            "reconnect_window_sec": 600,
            "idle_timeout_sec": 3600,
            "discard_unsaved_overlay_on_close": True,
            "discard_unsaved_overlay_on_idle_expire": True,
            "discard_on_close_paths": ["upper", "work"],
            "cow": {
                "mode": "copy_on_write",
                "base_dir": "base",
                "upper_dir": "upper",
                "work_dir": "work",
                "merged_dir": "merged",
            },
        },
    }


def _default_registry() -> dict[str, Any]:
    return {"version": 1, "policyId": "AXION_SANDBOX_PROJECTION_SESSION_REGISTRY_V1", "sessions": {}}


def _audit(event: dict[str, Any]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = dict(event)
    record.setdefault("ts", _now_iso())
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def load_policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        return _default_policy()
    return _load_json(POLICY_PATH)


def load_session_registry() -> dict[str, Any]:
    if not SESSION_REGISTRY_PATH.exists():
        reg = _default_registry()
        SESSION_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        _save_json(SESSION_REGISTRY_PATH, reg)
        return reg
    try:
        raw = _load_json(SESSION_REGISTRY_PATH)
    except Exception:
        reg = _default_registry()
        SESSION_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        _save_json(SESSION_REGISTRY_PATH, reg)
        return reg
    if not isinstance(raw, dict):
        reg = _default_registry()
        SESSION_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        _save_json(SESSION_REGISTRY_PATH, reg)
        return reg
    if not isinstance(raw.get("sessions"), dict):
        raw["sessions"] = {}
    raw.setdefault("version", 1)
    raw.setdefault("policyId", "AXION_SANDBOX_PROJECTION_SESSION_REGISTRY_V1")
    return raw


def save_session_registry(registry: dict[str, Any]) -> None:
    SESSION_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _save_json(SESSION_REGISTRY_PATH, registry)


def _session_root(policy: dict[str, Any]) -> Path:
    session_cfg = (policy.get("session") or {})
    return AXION_ROOT / str(session_cfg.get("session_root", "data/rootfs/Sandbox Projections/Sessions"))


def _cow_paths(policy: dict[str, Any], app_id: str, session_id: str) -> dict[str, str]:
    session_cfg = (policy.get("session") or {})
    cow = (session_cfg.get("cow") or {})
    root = _session_root(policy) / str(app_id) / str(session_id)
    return {
        "session_root": str(root),
        "base": str(root / str(cow.get("base_dir", "base"))),
        "upper": str(root / str(cow.get("upper_dir", "upper"))),
        "work": str(root / str(cow.get("work_dir", "work"))),
        "merged": str(root / str(cow.get("merged_dir", "merged"))),
        "mode": str(cow.get("mode", "copy_on_write")),
    }


def _parse_ts(raw: Any) -> float | None:
    try:
        text = str(raw or "").strip()
        if not text:
            return None
        return datetime.fromisoformat(text).timestamp()
    except Exception:
        return None


def _session_policy_flags(policy: dict[str, Any]) -> dict[str, Any]:
    session_cfg = dict((policy.get("session") or {}))
    discard_paths = session_cfg.get("discard_on_close_paths", ["upper", "work"])
    out_paths: list[str] = []
    for raw in discard_paths if isinstance(discard_paths, list) else []:
        token = str(raw or "").strip().lower()
        if token in ("upper", "work", "merged") and token not in out_paths:
            out_paths.append(token)
    if not out_paths:
        out_paths = ["upper", "work"]
    return {
        "discard_unsaved_overlay_on_close": bool(session_cfg.get("discard_unsaved_overlay_on_close", True)),
        "discard_unsaved_overlay_on_idle_expire": bool(session_cfg.get("discard_unsaved_overlay_on_idle_expire", True)),
        "discard_on_close_paths": out_paths,
    }


def _purge_runtime_overlay(entry: dict[str, Any], *, paths: list[str]) -> dict[str, Any]:
    layer = dict(entry.get("runtime_layer") or {})
    purged: list[str] = []
    errors: list[dict[str, str]] = []
    for key in paths:
        raw = str(layer.get(key) or "").strip()
        if not raw:
            continue
        target = Path(raw)
        try:
            if target.exists():
                for child in target.iterdir():
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
            target.mkdir(parents=True, exist_ok=True)
            purged.append(str(target))
        except Exception as ex:
            errors.append({"path": str(target), "error": str(ex)})
    return {
        "ok": len(errors) == 0,
        "code": "PROJECTION_SESSION_OVERLAY_PURGED" if len(errors) == 0 else "PROJECTION_SESSION_OVERLAY_PURGE_FAILED",
        "purged_paths": purged,
        "errors": errors,
    }


def _is_idle_expired(entry: dict[str, Any], now_ts: float) -> bool:
    timeout = int(entry.get("idle_timeout_sec", 0) or 0)
    if timeout <= 0:
        return False
    last_seen = _parse_ts(entry.get("last_seen_utc"))
    if last_seen is None:
        return True
    return (now_ts - last_seen) > timeout


def _is_reconnect_valid(entry: dict[str, Any], now_ts: float, reconnect_window_sec: int) -> bool:
    if not bool(entry.get("active", False)):
        return False
    if _is_idle_expired(entry, now_ts):
        return False
    last_seen = _parse_ts(entry.get("last_seen_utc"))
    if last_seen is None:
        return False
    return (now_ts - last_seen) <= max(1, int(reconnect_window_sec))


def _write_session_contract(session: dict[str, Any]) -> None:
    merged_raw = str(((session.get("runtime_layer") or {}).get("merged")) or "").strip()
    if not merged_raw:
        return
    merged = Path(merged_raw)
    merged.mkdir(parents=True, exist_ok=True)
    contract = merged / "session_contract.json"
    contract.write_text(
        json.dumps(
            {
                "session_id": session.get("session_id"),
                "app_id": session.get("app_id"),
                "projection_id": session.get("projection_id"),
                "runtime_layer": session.get("runtime_layer"),
                "reconnect_token": session.get("reconnect_token"),
                "updated_utc": session.get("last_seen_utc"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def reap_expired_sessions(corr: str | None = None) -> dict[str, Any]:
    policy = load_policy()
    flags = _session_policy_flags(policy)
    reg = load_session_registry()
    sessions = reg.setdefault("sessions", {})
    now_iso = _now_iso()
    now_ts = _parse_ts(now_iso) or 0.0
    expired_ids: list[str] = []
    for sid, item in sessions.items():
        if not isinstance(item, dict):
            continue
        if not bool(item.get("active", False)):
            continue
        if not _is_idle_expired(item, now_ts):
            continue
        item["active"] = False
        item["closed_utc"] = now_iso
        item["closed_reason"] = "idle_timeout"
        if bool(flags.get("discard_unsaved_overlay_on_idle_expire", True)):
            item["overlay_cleanup"] = _purge_runtime_overlay(
                item,
                paths=list(flags.get("discard_on_close_paths", ["upper", "work"])),
            )
        expired_ids.append(str(sid))
        _audit(
            {
                "event": "projection.session.expired",
                "session_id": sid,
                "app_id": item.get("app_id"),
                "reason": "idle_timeout",
                "corr": corr,
            }
        )

    if expired_ids:
        save_session_registry(reg)
    return {
        "ok": True,
        "code": "PROJECTION_SESSION_REAP_OK",
        "expired_count": len(expired_ids),
        "expired_ids": expired_ids,
    }


def get_active_session(app_id: str, projection_id: str | None = None) -> dict[str, Any] | None:
    reg = load_session_registry()
    sessions = reg.get("sessions", {})
    for item in sessions.values():
        if not isinstance(item, dict):
            continue
        if not bool(item.get("active", False)):
            continue
        if str(item.get("app_id")) != str(app_id):
            continue
        if projection_id and str(item.get("projection_id")) != str(projection_id):
            continue
        return item
    return None


def close_session(session_id: str, reason: str = "closed") -> dict[str, Any]:
    policy = load_policy()
    flags = _session_policy_flags(policy)
    reg = load_session_registry()
    sessions = reg.setdefault("sessions", {})
    entry = sessions.get(str(session_id))
    if not isinstance(entry, dict):
        return {"ok": False, "code": "PROJECTION_SESSION_NOT_FOUND", "session_id": session_id}
    entry["active"] = False
    entry["closed_utc"] = _now_iso()
    entry["closed_reason"] = str(reason)
    if bool(flags.get("discard_unsaved_overlay_on_close", True)):
        entry["overlay_cleanup"] = _purge_runtime_overlay(
            entry,
            paths=list(flags.get("discard_on_close_paths", ["upper", "work"])),
        )
    save_session_registry(reg)
    _audit({"event": "projection.session.closed", "session_id": session_id, "app_id": entry.get("app_id"), "reason": reason})
    return {
        "ok": True,
        "code": "PROJECTION_SESSION_CLOSED",
        "session_id": session_id,
        "overlay_cleanup": dict(entry.get("overlay_cleanup") or {}),
    }


def start_or_reconnect_session(app_id: str, projection: dict[str, Any], corr: str | None = None) -> dict[str, Any]:
    policy = load_policy()
    flags = _session_policy_flags(policy)
    session_cfg = (policy.get("session") or {})
    reconnect_window_sec = int(session_cfg.get("reconnect_window_sec", 600))
    idle_timeout_sec = int(session_cfg.get("idle_timeout_sec", 3600))
    reg = load_session_registry()
    sessions = reg.setdefault("sessions", {})
    reap_expired_sessions(corr=corr)
    reg = load_session_registry()
    sessions = reg.setdefault("sessions", {})
    now_iso = _now_iso()
    now_ts = datetime.fromisoformat(now_iso).timestamp()
    app_id = str(app_id)
    projection_id = str((projection or {}).get("projection_id", ""))

    for sid, item in sessions.items():
        if not isinstance(item, dict):
            continue
        if str(item.get("app_id")) != app_id:
            continue
        if projection_id and str(item.get("projection_id")) != projection_id:
            continue
        if _is_reconnect_valid(item, now_ts, reconnect_window_sec):
            item["last_seen_utc"] = now_iso
            item["reconnect_count"] = int(item.get("reconnect_count", 0)) + 1
            save_session_registry(reg)
            _write_session_contract(item)
            _audit(
                {
                    "event": "projection.session.reconnected",
                    "session_id": sid,
                    "app_id": app_id,
                    "projection_id": projection_id,
                    "corr": corr,
                }
            )
            return {"ok": True, "code": "PROJECTION_SESSION_RECONNECTED", "session": item}

    session_id = f"{app_id}-{secrets.token_hex(8)}"
    layer = _cow_paths(policy, app_id=app_id, session_id=session_id)
    Path(layer["base"]).mkdir(parents=True, exist_ok=True)
    Path(layer["upper"]).mkdir(parents=True, exist_ok=True)
    Path(layer["work"]).mkdir(parents=True, exist_ok=True)
    Path(layer["merged"]).mkdir(parents=True, exist_ok=True)

    session = {
        "session_id": session_id,
        "app_id": app_id,
        "projection_id": projection_id,
        "projection_root": projection.get("projection_root"),
        "environment_root": projection.get("environment_root"),
        "active": True,
        "created_utc": now_iso,
        "last_seen_utc": now_iso,
        "idle_timeout_sec": idle_timeout_sec,
        "reconnect_window_sec": reconnect_window_sec,
        "reconnect_count": 0,
        "reconnect_token": secrets.token_hex(12),
        "discard_unsaved_overlay_on_close": bool(flags.get("discard_unsaved_overlay_on_close", True)),
        "discard_unsaved_overlay_on_idle_expire": bool(flags.get("discard_unsaved_overlay_on_idle_expire", True)),
        "discard_on_close_paths": list(flags.get("discard_on_close_paths", ["upper", "work"])),
        "runtime_layer": layer,
    }
    sessions[session_id] = session
    save_session_registry(reg)
    _write_session_contract(session)
    _audit(
        {
            "event": "projection.session.started",
            "session_id": session_id,
            "app_id": app_id,
            "projection_id": projection_id,
            "corr": corr,
        }
    )
    return {"ok": True, "code": "PROJECTION_SESSION_STARTED", "session": session}


def heartbeat_session(session_id: str, corr: str | None = None) -> dict[str, Any]:
    policy = load_policy()
    flags = _session_policy_flags(policy)
    reg = load_session_registry()
    sessions = reg.setdefault("sessions", {})
    item = sessions.get(str(session_id))
    if not isinstance(item, dict):
        return {"ok": False, "code": "PROJECTION_SESSION_NOT_FOUND", "session_id": session_id}
    if not bool(item.get("active", False)):
        return {"ok": False, "code": "PROJECTION_SESSION_INACTIVE", "session_id": session_id}
    now_iso = _now_iso()
    now_ts = _parse_ts(now_iso) or 0.0
    if _is_idle_expired(item, now_ts):
        item["active"] = False
        item["closed_utc"] = now_iso
        item["closed_reason"] = "idle_timeout"
        if bool(flags.get("discard_unsaved_overlay_on_idle_expire", True)):
            item["overlay_cleanup"] = _purge_runtime_overlay(
                item,
                paths=list(flags.get("discard_on_close_paths", ["upper", "work"])),
            )
        save_session_registry(reg)
        _audit(
            {
                "event": "projection.session.expired",
                "session_id": session_id,
                "app_id": item.get("app_id"),
                "reason": "idle_timeout",
                "corr": corr,
            }
        )
        return {"ok": False, "code": "PROJECTION_SESSION_EXPIRED", "session_id": session_id}
    item["last_seen_utc"] = _now_iso()
    save_session_registry(reg)
    _write_session_contract(item)
    _audit({"event": "projection.session.heartbeat", "session_id": session_id, "app_id": item.get("app_id"), "corr": corr})
    return {"ok": True, "code": "PROJECTION_SESSION_HEARTBEAT_OK", "session": item}
