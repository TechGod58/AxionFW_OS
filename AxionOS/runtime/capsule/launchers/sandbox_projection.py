from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AXION_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = AXION_ROOT / "config" / "SANDBOX_PROJECTION_POLICY_V1.json"
REGISTRY_PATH = AXION_ROOT / "config" / "SANDBOX_PROJECTION_REGISTRY_V1.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _slug(value: str) -> str:
    out = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(value or "").strip().lower())
    out = out.strip("._-")
    return out or "external_program"


def _default_policy() -> dict[str, Any]:
    return {
        "version": 1,
        "policyId": "AXION_SANDBOX_PROJECTION_POLICY_V1",
        "roots": {
            "projection_root": "data/rootfs/Sandbox Projections/Catalog",
            "environment_root": "data/rootfs/Sandbox Projections/Environments",
        },
        "launch_projection_required": True,
        "projection_state_file": "projection.json",
    }


def _default_registry() -> dict[str, Any]:
    return {"version": 1, "policyId": "AXION_SANDBOX_PROJECTION_REGISTRY_V1", "apps": {}}


def load_projection_policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        return _default_policy()
    return _load_json(POLICY_PATH)


def load_projection_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        reg = _default_registry()
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        _save_json(REGISTRY_PATH, reg)
        return reg
    try:
        raw = _load_json(REGISTRY_PATH)
    except Exception:
        reg = _default_registry()
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        _save_json(REGISTRY_PATH, reg)
        return reg
    if not isinstance(raw, dict):
        reg = _default_registry()
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        _save_json(REGISTRY_PATH, reg)
        return reg
    if not isinstance(raw.get("apps"), dict):
        raw["apps"] = {}
    raw.setdefault("version", 1)
    raw.setdefault("policyId", "AXION_SANDBOX_PROJECTION_REGISTRY_V1")
    return raw


def save_projection_registry(registry: dict[str, Any]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _save_json(REGISTRY_PATH, registry)


def projection_app_id(app_id: str | None = None, installer_path: str | None = None) -> str:
    if app_id:
        return _slug(str(app_id))
    stem = Path(str(installer_path or "external_program")).stem
    return _slug(stem)


def get_projection(app_id: str) -> dict[str, Any] | None:
    reg = load_projection_registry()
    entry = reg.get("apps", {}).get(str(app_id))
    if not isinstance(entry, dict):
        return None
    if not bool(entry.get("active", True)):
        return None
    return entry


def ensure_projection(
    app_id: str,
    family: str,
    profile: str,
    execution_model: str,
    source: str,
    installer_path: str | None = None,
) -> dict[str, Any]:
    policy = load_projection_policy()
    reg = load_projection_registry()

    roots = policy.get("roots", {})
    projection_root = AXION_ROOT / str(roots.get("projection_root", "data/rootfs/Sandbox Projections/Catalog"))
    environment_root = AXION_ROOT / str(roots.get("environment_root", "data/rootfs/Sandbox Projections/Environments"))
    state_file = str(policy.get("projection_state_file", "projection.json"))

    app_key = projection_app_id(app_id=app_id)
    projection_id = f"{app_key}:{family}:{profile}"

    catalog_dir = projection_root / app_key
    env_dir = environment_root / app_key
    catalog_dir.mkdir(parents=True, exist_ok=True)
    env_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "projection_id": projection_id,
        "app_id": app_key,
        "family": str(family),
        "profile": str(profile),
        "execution_model": str(execution_model),
        "active": True,
        "source": str(source),
        "installer_artifact": Path(installer_path).name if installer_path else None,
        "projection_root": str(catalog_dir),
        "environment_root": str(env_dir),
        "updated_utc": _now_iso(),
        "launch_contract": {"run_from_projection": True, "stable_environment": True},
    }

    (catalog_dir / state_file).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    (env_dir / "runtime_env.json").write_text(
        json.dumps(
            {
                "app_id": app_key,
                "family": record["family"],
                "profile": record["profile"],
                "execution_model": record["execution_model"],
                "projection_id": projection_id,
                "updated_utc": record["updated_utc"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    reg.setdefault("apps", {})[app_key] = record
    save_projection_registry(reg)
    return record
