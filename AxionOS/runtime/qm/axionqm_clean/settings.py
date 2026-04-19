from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def workspace_root() -> Path:
    current = repo_root()
    for candidate in (current, *current.parents):
        if (candidate / "workspace_manifest.json").exists():
            return candidate
    return current.parent


def _resolve(base: Path, raw: str | None) -> Path | None:
    if raw is None:
        return None
    path = Path(raw)
    if path.is_absolute():
        return path
    return (base / path).resolve()


@dataclass(frozen=True)
class QMSettings:
    root_dir: Path
    profile: str
    recovery_window_steps: int
    rollback_cooldown_steps: int
    em_enabled: bool
    em_root: Path | None
    em_config_path: Path | None

    @classmethod
    def load(cls, settings_path: Path | None = None) -> "QMSettings":
        root = repo_root()
        workspace = workspace_root()
        path = settings_path or (root / "config" / "defaults.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        em = payload.get("em_bridge", {})
        manifest_paths = {}
        manifest_path = workspace / "workspace_manifest.json"
        if manifest_path.exists():
            manifest_paths = json.loads(manifest_path.read_text(encoding="utf-8")).get("paths", {})
        em_root_raw = manifest_paths.get("em_root", em.get("em_root"))
        em_config_raw = em.get("config_path")
        if em_config_raw is None and em_root_raw:
            em_config_raw = str(Path(em_root_raw) / "config" / "defaults.json")
        return cls(
            root_dir=root,
            profile=str(payload.get("profile", "balanced")),
            recovery_window_steps=int(payload.get("recovery_window_steps", 2)),
            rollback_cooldown_steps=int(payload.get("rollback_cooldown_steps", 3)),
            em_enabled=bool(em.get("enabled", False)),
            em_root=_resolve(workspace, em_root_raw),
            em_config_path=_resolve(workspace, em_config_raw),
        )
