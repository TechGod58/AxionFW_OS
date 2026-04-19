import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import sys

_TOOLS_DIR = None
for _parent in Path(__file__).resolve().parents:
    if (_parent / "tools" / "common" / "pathing.py").exists():
        _TOOLS_DIR = _parent / "tools"
        break
if _TOOLS_DIR and str(_TOOLS_DIR) not in sys.path:
    sys.path.append(str(_TOOLS_DIR))

from common.pathing import axion_path, axion_os_root


def axion_path_str(*parts):
    return str(axion_path(*parts))


POLICY_PATH = Path(axion_path_str("config", "SHADOW_COPY_POLICY_V1.json"))
STATE_PATH = Path(axion_path_str("config", "SHADOW_COPY_STATE_V1.json"))
SHADOW_ROOT = Path(axion_path_str("data", "shadow_copies"))
SHADOW_ROOT.mkdir(parents=True, exist_ok=True)
_AXION_ROOT = axion_os_root().resolve()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _read_json(path: Path, default: dict[str, Any]):
    if not path.exists():
        return dict(default)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return dict(default)


def _write_json(path: Path, payload: dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_policy() -> dict[str, Any]:
    default = {
        "version": 1,
        "enabled": True,
        "default_scope_id": "system",
        "schedule": {
            "enabled": True,
            "frequency": "weekly",
            "interval_weeks": 1,
            "day_utc": "sunday",
            "time_utc": "03:00",
        },
        "retention": {"max_copies": 8, "delete_oldest_first": True},
        "targets": ["data/profiles/p1/Workspace"],
    }
    policy = _read_json(POLICY_PATH, default)
    policy.setdefault("schedule", {})
    policy.setdefault("retention", {})
    policy.setdefault("targets", [])
    policy["retention"]["max_copies"] = max(1, int(policy["retention"].get("max_copies", 8) or 8))
    return policy


def _load_state() -> dict[str, Any]:
    default = {"version": 1, "policyId": "AXION_SHADOW_COPY_STATE_V1", "scopes": {}}
    state = _read_json(STATE_PATH, default)
    scopes = state.get("scopes")
    if not isinstance(scopes, dict):
        state["scopes"] = {}
    return state


def _save_state(state: dict[str, Any]):
    _write_json(STATE_PATH, state)


def _safe_rel(abs_path: Path) -> str | None:
    try:
        rel = abs_path.resolve().relative_to(_AXION_ROOT)
        return str(rel).replace("\\", "/")
    except Exception:
        return None


def _resolve_targets(target_paths: list[str] | None = None) -> list[Path]:
    policy = load_policy()
    raw = target_paths if isinstance(target_paths, list) and target_paths else list(policy.get("targets", []))
    out: list[Path] = []
    for entry in raw:
        value = str(entry or "").strip().replace("\\", "/")
        if not value:
            continue
        target = (_AXION_ROOT / value).resolve()
        rel = _safe_rel(target)
        if rel is None:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.suffix:
            if not target.exists():
                target.write_text("", encoding="utf-8")
        else:
            target.mkdir(parents=True, exist_ok=True)
        out.append(target)
    return out


def _scope_root(scope_id: str) -> Path:
    return SHADOW_ROOT / str(scope_id or "system").strip()


def _snapshot_root(scope_id: str, snapshot_id: str) -> Path:
    return _scope_root(scope_id) / snapshot_id


def _list_snapshot_metadata(scope_id: str) -> list[dict[str, Any]]:
    root = _scope_root(scope_id)
    if not root.exists():
        return []
    out = []
    for snap in sorted(root.iterdir(), key=lambda p: p.name):
        meta_path = snap / "snapshot.json"
        if not meta_path.exists():
            continue
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8-sig"))
            if isinstance(payload, dict):
                out.append(payload)
        except Exception:
            continue
    return sorted(out, key=lambda item: str(item.get("created_utc", "")), reverse=True)


def list_shadow_copies(scope_id: str | None = None):
    policy = load_policy()
    scope = str(scope_id or policy.get("default_scope_id") or "system").strip()
    snapshots = _list_snapshot_metadata(scope)
    return {
        "ok": True,
        "code": "SHADOW_COPY_LIST_OK",
        "scope_id": scope,
        "count": len(snapshots),
        "schedule": dict(policy.get("schedule", {})),
        "retention": dict(policy.get("retention", {})),
        "snapshots": snapshots,
    }


def _copy_target_to_payload(target: Path, payload_root: Path, index: int) -> dict[str, Any]:
    rel = _safe_rel(target)
    if rel is None:
        return {"ok": False, "code": "SHADOW_COPY_TARGET_OUTSIDE_ROOT", "target": str(target)}
    target_name = rel.replace("/", "__")
    slot = payload_root / f"{index:03d}_{target_name}"
    if target.is_dir():
        shutil.copytree(target, slot, dirs_exist_ok=False)
        kind = "directory"
    else:
        slot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, slot)
        kind = "file"
    return {
        "ok": True,
        "target_rel": rel,
        "target_abs": str(target),
        "kind": kind,
        "snapshot_slot": str(slot.relative_to(payload_root.parent)).replace("\\", "/"),
    }


def _enforce_retention(scope_id: str, max_copies: int) -> list[str]:
    entries = _list_snapshot_metadata(scope_id)
    keep = max(1, int(max_copies))
    removed: list[str] = []
    for stale in entries[keep:]:
        snap_id = str(stale.get("snapshot_id", "")).strip()
        if not snap_id:
            continue
        root = _snapshot_root(scope_id, snap_id)
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
            removed.append(snap_id)
    return removed


def create_shadow_copy(
    *,
    reason: str = "manual",
    scope_id: str | None = None,
    target_paths: list[str] | None = None,
    created_utc: str | None = None,
):
    policy = load_policy()
    if not bool(policy.get("enabled", True)):
        return {"ok": False, "code": "SHADOW_COPY_DISABLED"}

    scope = str(scope_id or policy.get("default_scope_id") or "system").strip()
    now = datetime.fromisoformat(created_utc) if created_utc else _now_utc()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    snapshot_id = f"sc_{now.strftime('%Y%m%dT%H%M%S%fZ')}"
    snap_root = _snapshot_root(scope, snapshot_id)
    payload_root = snap_root / "payload"
    payload_root.mkdir(parents=True, exist_ok=False)

    targets = _resolve_targets(target_paths=target_paths)
    if not targets:
        shutil.rmtree(snap_root, ignore_errors=True)
        return {"ok": False, "code": "SHADOW_COPY_NO_TARGETS", "scope_id": scope}

    copied: list[dict[str, Any]] = []
    for idx, target in enumerate(targets, start=1):
        copied.append(_copy_target_to_payload(target, payload_root, idx))

    meta = {
        "snapshot_id": snapshot_id,
        "scope_id": scope,
        "created_utc": now.isoformat(),
        "reason": str(reason or "manual"),
        "targets": copied,
        "policy_schedule": dict(policy.get("schedule", {})),
        "retention_max": int(policy.get("retention", {}).get("max_copies", 8) or 8),
    }
    _write_json(snap_root / "snapshot.json", meta)

    state = _load_state()
    scopes = state.setdefault("scopes", {})
    record = scopes.setdefault(scope, {})
    record["last_snapshot_id"] = snapshot_id
    record["last_snapshot_utc"] = now.isoformat()
    _save_state(state)

    removed = _enforce_retention(scope, int(policy.get("retention", {}).get("max_copies", 8) or 8))
    return {
        "ok": True,
        "code": "SHADOW_COPY_CREATED",
        "scope_id": scope,
        "snapshot_id": snapshot_id,
        "created_utc": now.isoformat(),
        "targets_count": len(copied),
        "removed_for_retention": removed,
    }


def rollback_shadow_copy(snapshot_id: str, *, scope_id: str | None = None):
    policy = load_policy()
    scope = str(scope_id or policy.get("default_scope_id") or "system").strip()
    snap = _snapshot_root(scope, str(snapshot_id))
    meta_path = snap / "snapshot.json"
    if not meta_path.exists():
        return {"ok": False, "code": "SHADOW_COPY_NOT_FOUND", "snapshot_id": str(snapshot_id), "scope_id": scope}

    meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    restored: list[str] = []
    for target in meta.get("targets", []):
        rel = str((target or {}).get("target_rel", "")).strip()
        slot = str((target or {}).get("snapshot_slot", "")).strip()
        if not rel or not slot:
            continue
        dst = (_AXION_ROOT / rel).resolve()
        src = (snap / slot).resolve()
        if _safe_rel(dst) is None:
            continue
        if not src.exists():
            continue
        if dst.exists():
            if dst.is_dir():
                shutil.rmtree(dst, ignore_errors=True)
            else:
                dst.unlink(missing_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=False)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        restored.append(rel)

    state = _load_state()
    scopes = state.setdefault("scopes", {})
    record = scopes.setdefault(scope, {})
    record["last_rollback_snapshot_id"] = str(snapshot_id)
    record["last_rollback_utc"] = _now_utc().isoformat()
    _save_state(state)
    return {
        "ok": True,
        "code": "SHADOW_COPY_ROLLBACK_OK",
        "scope_id": scope,
        "snapshot_id": str(snapshot_id),
        "restored_count": len(restored),
        "restored_targets": restored,
    }


def _parse_iso(value: str | None) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def run_shadow_copy_maintenance(
    *,
    scope_id: str | None = None,
    force: bool = False,
    now_utc: str | None = None,
    target_paths: list[str] | None = None,
):
    policy = load_policy()
    schedule = dict(policy.get("schedule", {}))
    scope = str(scope_id or policy.get("default_scope_id") or "system").strip()
    now = _parse_iso(now_utc) or _now_utc()
    if not bool(schedule.get("enabled", True)):
        return {"ok": True, "code": "SHADOW_COPY_MAINTENANCE_DISABLED", "scope_id": scope}

    state = _load_state()
    last = _parse_iso((((state.get("scopes") or {}).get(scope) or {}).get("last_snapshot_utc")))
    due = True
    if last is not None:
        interval_weeks = max(1, int(schedule.get("interval_weeks", 1) or 1))
        due = now >= (last + timedelta(weeks=interval_weeks))
    if (not due) and (not bool(force)):
        return {
            "ok": True,
            "code": "SHADOW_COPY_MAINTENANCE_SKIPPED_NOT_DUE",
            "scope_id": scope,
            "last_snapshot_utc": last.isoformat() if last else None,
            "next_due_utc": (last + timedelta(weeks=max(1, int(schedule.get("interval_weeks", 1) or 1)))).isoformat() if last else None,
        }

    created = create_shadow_copy(
        reason="scheduled_weekly",
        scope_id=scope,
        target_paths=target_paths,
        created_utc=now.isoformat(),
    )
    created["maintenance"] = {
        "frequency": str(schedule.get("frequency", "weekly")),
        "interval_weeks": max(1, int(schedule.get("interval_weeks", 1) or 1)),
        "retention_max": int(policy.get("retention", {}).get("max_copies", 8) or 8),
    }
    return created


if __name__ == "__main__":
    print(json.dumps(list_shadow_copies(), indent=2))
