import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FOLDERS_PATH = ROOT / "config" / "PROFILE_SHELL_FOLDERS_V1.json"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_folders():
    return json.loads(FOLDERS_PATH.read_text(encoding="utf-8-sig"))


def _profile_root(profile: str = "p1") -> Path:
    return ROOT / "data" / "profiles" / str(profile)


def _folder_entries(profile: str = "p1"):
    cfg = _load_folders()
    folders = cfg.get("folders", {})
    out = []
    root = _profile_root(profile)
    root.mkdir(parents=True, exist_ok=True)
    for key, meta in folders.items():
        if not isinstance(meta, dict):
            continue
        segment = str(meta.get("pathSegment", key))
        folder_path = root / segment
        folder_path.mkdir(parents=True, exist_ok=True)
        out.append(
            {
                "id": str(key),
                "display_name": str(meta.get("displayName", segment)),
                "path": str(folder_path),
                "sandbox_kind": str(meta.get("sandboxKind", "persistent_profile_sandbox")),
                "never_destroy_on_close": bool(meta.get("neverDestroyOnClose", True)),
            }
        )
    return sorted(out, key=lambda item: item["display_name"].lower())


def _resolve_profile_folder(folder: str, profile: str = "p1"):
    wanted = str(folder or "Workspace").strip().lower()
    cfg = _load_folders()
    folders = cfg.get("folders", {})
    for entry in _folder_entries(profile=profile):
        meta = dict(folders.get(entry["id"], {}) or {})
        aliases = {
            entry["id"].lower(),
            entry["display_name"].lower(),
            str(meta.get("pathSegment", "")).strip().lower(),
            str(meta.get("legacyAlias", "")).strip().lower(),
            str(meta.get("windowsBehavior", "")).strip().lower(),
        }
        for field in ("aliases", "displayAliases", "pathSegmentAliases"):
            values = meta.get(field)
            if isinstance(values, list):
                aliases.update(str(x).strip().lower() for x in values if str(x).strip())
        if wanted in aliases:
            return entry
    return None


def _safe_resolve(path: str, profile: str = "p1"):
    candidate = Path(path).resolve()
    root = _profile_root(profile).resolve()
    if root == candidate or root in candidate.parents:
        return {"ok": True, "path": candidate, "profile_root": root}
    return {"ok": False, "code": "FILE_EXPLORER_OUTSIDE_PROFILE_BLOCKED", "path": str(candidate), "profile_root": str(root)}


def _list_path(path: Path, limit: int = 256):
    items = []
    for child in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        st = child.stat()
        items.append(
            {
                "name": child.name,
                "path": str(child),
                "kind": "directory" if child.is_dir() else "file",
                "bytes": int(st.st_size),
                "modified_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
            }
        )
        if len(items) >= max(1, int(limit)):
            break
    return items


def snapshot(profile: str = "p1"):
    cfg = _load_folders()
    return {
        "ok": True,
        "code": "FILE_EXPLORER_SNAPSHOT_OK",
        "app": "File Explorer",
        "app_id": "file_explorer",
        "profile": str(profile),
        "profile_root": str(_profile_root(profile)),
        "save_policy": dict(cfg.get("savePolicy", {})),
        "folders": _folder_entries(profile=profile),
        "updated_utc": _now_iso(),
    }


def list_folder(folder: str = "Workspace", profile: str = "p1", limit: int = 256):
    entry = _resolve_profile_folder(folder, profile=profile)
    if entry is None:
        return {
            "ok": False,
            "code": "FILE_EXPLORER_FOLDER_UNKNOWN",
            "folder": str(folder),
        }
    target = Path(entry["path"])
    target.mkdir(parents=True, exist_ok=True)
    return {
        "ok": True,
        "code": "FILE_EXPLORER_LIST_OK",
        "folder": entry["display_name"],
        "path": str(target),
        "items": _list_path(target, limit=limit),
    }


def open_entry(path: str, profile: str = "p1"):
    safe = _safe_resolve(path, profile=profile)
    if not bool(safe.get("ok")):
        return safe
    target = Path(str(safe["path"]))
    if not target.exists():
        return {"ok": False, "code": "FILE_EXPLORER_ENTRY_MISSING", "path": str(target)}
    st = target.stat()
    return {
        "ok": True,
        "code": "FILE_EXPLORER_OPEN_OK",
        "path": str(target),
        "kind": "directory" if target.is_dir() else "file",
        "bytes": int(st.st_size),
        "modified_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
    }


def search(folder: str, query: str, profile: str = "p1", limit: int = 128):
    listed = list_folder(folder=folder, profile=profile, limit=4096)
    if not bool(listed.get("ok")):
        return listed
    needle = str(query or "").strip().lower()
    if not needle:
        return {"ok": False, "code": "FILE_EXPLORER_QUERY_EMPTY"}
    matches = [item for item in listed["items"] if needle in str(item.get("name", "")).lower()]
    return {
        "ok": True,
        "code": "FILE_EXPLORER_SEARCH_OK",
        "folder": listed["folder"],
        "query": needle,
        "matches": matches[: max(1, int(limit))],
    }


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
