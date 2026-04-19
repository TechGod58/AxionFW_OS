from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AXION_ROOT = Path(__file__).resolve().parents[3]
PROGRAM_LAYOUT_PATH = AXION_ROOT / "config" / "program_layout.json"
REGISTRY_PATH = AXION_ROOT / "config" / "INSTALL_SANDBOX_REGISTRY_V1.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    out = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(value or "").strip().lower())
    out = out.strip("._-")
    return out or "external_program"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _default_layout() -> dict[str, Any]:
    return {
        "version": "1.1",
        "program_layout": {
            "program_files": {"name": "Program Files", "path": "Program Files", "arch": "x64"},
            "program_files_x86": {"name": "Program Files (86)", "path": "Program Files (86)", "arch": "x86"},
            "program_modules": {"name": "Program Modules", "path": "Program Modules", "arch": "shared"},
            "sandbox_projections": {"name": "Sandbox Projections", "path": "Sandbox Projections", "arch": "shared"},
        },
    }


def _default_registry() -> dict[str, Any]:
    return {
        "version": 1,
        "policyId": "AXION_INSTALL_SANDBOX_REGISTRY_V1",
        "images": {},
        "last_updated_utc": None,
    }


def load_program_layout() -> dict[str, Any]:
    if not PROGRAM_LAYOUT_PATH.exists():
        return _default_layout()
    try:
        obj = _load_json(PROGRAM_LAYOUT_PATH)
    except Exception:
        return _default_layout()
    return obj if isinstance(obj, dict) else _default_layout()


def load_install_registry() -> dict[str, Any]:
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
    if not isinstance(raw.get("images"), dict):
        raw["images"] = {}
    raw.setdefault("version", 1)
    raw.setdefault("policyId", "AXION_INSTALL_SANDBOX_REGISTRY_V1")
    raw.setdefault("last_updated_utc", None)
    return raw


def save_install_registry(registry: dict[str, Any]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _save_json(REGISTRY_PATH, registry)


def _windows_prefers_x86(profile: str, installer_artifact: str) -> bool:
    profile_key = str(profile or "").strip().lower()
    artifact = str(installer_artifact or "").strip().lower()
    if any(token in artifact for token in ("x86", "win32", "_86", "-86", "32bit", "x32")):
        return True
    # Legacy Windows profiles are modeled as x86 compatibility by default.
    return profile_key in {"win95", "win98", "winme", "win2000", "winxp"}


def _root_path_for_install(*, family: str, profile: str, installer_artifact: str) -> str:
    layout = load_program_layout()
    roots = dict(layout.get("program_layout") or {})
    rootfs = AXION_ROOT / "data" / "rootfs"
    family_key = str(family or "").strip().lower()
    if family_key == "windows" and _windows_prefers_x86(profile, installer_artifact):
        rel = str((roots.get("program_files_x86") or {}).get("path") or "Program Files (86)")
        return str(rootfs / rel)
    if family_key in {"windows", "linux"}:
        rel = str((roots.get("program_files") or {}).get("path") or "Program Files")
        return str(rootfs / rel)
    rel = str((roots.get("program_modules") or {}).get("path") or "Program Modules")
    return str(rootfs / rel)


def prepare_installer_runtime_context(
    *,
    app_id: str,
    family: str,
    profile: str,
    execution_model: str,
    installer_path: str,
    projection: dict[str, Any] | None = None,
    corr: str | None = None,
) -> dict[str, Any]:
    app_key = _slug(app_id)
    artifact = Path(str(installer_path)).name
    root = Path(_root_path_for_install(family=family, profile=profile, installer_artifact=artifact))
    install_dir = root / app_key
    install_dir.mkdir(parents=True, exist_ok=True)

    projection_root = str((projection or {}).get("projection_root") or "")
    environment_root = str((projection or {}).get("environment_root") or "")
    if projection_root:
        Path(projection_root).mkdir(parents=True, exist_ok=True)
    if environment_root:
        Path(environment_root).mkdir(parents=True, exist_ok=True)

    context = {
        "app_id": app_key,
        "family": str(family),
        "profile": str(profile),
        "execution_model": str(execution_model),
        "installer_path": str(installer_path),
        "installer_artifact": artifact,
        "install_root": str(root),
        "install_path": str(install_dir),
        "projection_root": projection_root or None,
        "environment_root": environment_root or None,
        "corr": corr,
        "updated_utc": _now_iso(),
    }
    (install_dir / "install_runtime_context.json").write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
    return context


def find_runtime_image(app_id: str) -> dict[str, Any] | None:
    app_key = _slug(app_id)
    reg = load_install_registry()
    images = reg.get("images") or {}
    if not isinstance(images, dict):
        return None
    candidates: list[dict[str, Any]] = []
    for row in images.values():
        if not isinstance(row, dict):
            continue
        if str(row.get("app_id") or "") != app_key:
            continue
        candidates.append(dict(row))
    if not candidates:
        return None
    candidates.sort(key=lambda x: str(x.get("updated_utc") or ""), reverse=True)
    return candidates[0]


def register_installer_runtime_image(
    *,
    app_id: str,
    family: str,
    profile: str,
    execution_model: str,
    installer_path: str,
    projection: dict[str, Any] | None,
    provenance_check: dict[str, Any] | None = None,
    replay_signature: str | None = None,
    corr: str | None = None,
) -> dict[str, Any]:
    app_key = _slug(app_id)
    artifact = Path(str(installer_path)).name
    root = Path(_root_path_for_install(family=family, profile=profile, installer_artifact=artifact))
    install_dir = root / app_key
    install_dir.mkdir(parents=True, exist_ok=True)
    projection_root = str((projection or {}).get("projection_root") or "")
    environment_root = str((projection or {}).get("environment_root") or "")
    image_id = f"{app_key}:{str(family)}:{str(profile)}"

    image = {
        "image_id": image_id,
        "app_id": app_key,
        "family": str(family),
        "profile": str(profile),
        "execution_model": str(execution_model),
        "installer_artifact": artifact,
        "installer_path": str(installer_path),
        "install_root": str(root),
        "install_path": str(install_dir),
        "projection_id": str((projection or {}).get("projection_id") or ""),
        "projection_root": projection_root or None,
        "environment_root": environment_root or None,
        "launch_mode": "projection_copy_on_write",
        "runtime_contract": {
            "install_in_sandbox": True,
            "environment_prepared_at_install": True,
            "launch_as_runtime_image": True,
            "overlay_mode": "copy_on_write",
        },
        "provenance_subject_hash": str((provenance_check or {}).get("subject_hash") or ""),
        "provenance_key_id": str((provenance_check or {}).get("trusted_key_id") or ""),
        "replay_signature": str(replay_signature or ""),
        "corr": corr,
        "updated_utc": _now_iso(),
    }

    manifest_path = install_dir / "install_sandbox_manifest.json"
    _save_json(manifest_path, image)

    if projection_root:
        projection_manifest = Path(projection_root) / "runtime_image_manifest.json"
        projection_manifest.parent.mkdir(parents=True, exist_ok=True)
        _save_json(
            projection_manifest,
            {
                "image_id": image_id,
                "app_id": app_key,
                "projection_id": image.get("projection_id"),
                "launch_mode": "projection_copy_on_write",
                "install_manifest_path": str(manifest_path),
                "updated_utc": image["updated_utc"],
            },
        )
    if environment_root:
        env_manifest = Path(environment_root) / "runtime_environment_manifest.json"
        env_manifest.parent.mkdir(parents=True, exist_ok=True)
        _save_json(
            env_manifest,
            {
                "image_id": image_id,
                "app_id": app_key,
                "family": str(family),
                "profile": str(profile),
                "execution_model": str(execution_model),
                "environment_prepared_at_install": True,
                "updated_utc": image["updated_utc"],
            },
        )

    reg = load_install_registry()
    reg.setdefault("images", {})[image_id] = image
    reg["last_updated_utc"] = image["updated_utc"]
    save_install_registry(reg)
    return {
        "ok": True,
        "code": "INSTALL_SANDBOX_RUNTIME_IMAGE_REGISTERED",
        "image": image,
        "manifest_path": str(manifest_path),
    }
