import hashlib
import json
from datetime import datetime, timezone
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

from common.pathing import axion_path


def axion_path_str(*parts):
    return str(axion_path(*parts))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        pass
    return dict(default)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _app_root(app_id: str) -> Path:
    root = Path(axion_path_str("data", "apps", app_id))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _documents_root(app_id: str) -> Path:
    root = _app_root(app_id) / "documents"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _exports_root(app_id: str) -> Path:
    root = _app_root(app_id) / "exports"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _state_path(app_id: str) -> Path:
    return _app_root(app_id) / "state.json"


def _normalize_name(doc_name: str | None) -> str:
    candidate = str(doc_name or "").strip()
    if not candidate:
        return "default"
    safe = []
    for ch in candidate:
        if ch.isalnum() or ch in ("-", "_", "."):
            safe.append(ch)
        else:
            safe.append("_")
    return ("".join(safe).strip("._") or "default").lower()


def _doc_path(app_id: str, doc_name: str | None, extension: str) -> Path:
    ext = str(extension or "").strip().lower()
    if not ext.startswith("."):
        ext = f".{ext}" if ext else ".txt"
    return _documents_root(app_id) / f"{_normalize_name(doc_name)}{ext}"


def _load_state(app_id: str) -> dict[str, Any]:
    return _read_json(
        _state_path(app_id),
        {
            "app_id": app_id,
            "version": 1,
            "documents_opened": 0,
            "documents_edited": 0,
            "documents_exported": 0,
            "last_opened": None,
            "last_edited": None,
            "last_exported": None,
            "updated_utc": None,
        },
    )


def _save_state(app_id: str, state: dict[str, Any]) -> None:
    state["updated_utc"] = _now_iso()
    _write_json(_state_path(app_id), state)


def _default_doc_payload(app_id: str, app_name: str, doc_name: str) -> str:
    return "\n".join(
        [
            f"# {app_name} Document",
            f"app_id={app_id}",
            f"doc={doc_name}",
            "seed=axion_productivity_runtime_v1",
            "",
        ]
    )


def _doc_result(code: str, path: Path, content: str, **extra) -> dict[str, Any]:
    out = {
        "ok": True,
        "code": code,
        "file": str(path),
        "bytes": len(content.encode("utf-8")),
        "sha256": _sha256_text(content),
        "content": content,
    }
    out.update(extra)
    return out


def open_document(*, app_id: str, app_name: str, doc_name: str | None, default_extension: str) -> dict[str, Any]:
    target = _doc_path(app_id, doc_name, default_extension)
    if not target.exists():
        target.write_text(_default_doc_payload(app_id, app_name, _normalize_name(doc_name)), encoding="utf-8")
    content = target.read_text(encoding="utf-8-sig")
    state = _load_state(app_id)
    state["documents_opened"] = int(state.get("documents_opened", 0)) + 1
    state["last_opened"] = str(target)
    _save_state(app_id, state)
    return _doc_result(
        "PRODUCTIVITY_OPEN_OK",
        target,
        content,
        app_id=app_id,
        app=app_name,
        document_name=target.name,
    )


def edit_document(
    *,
    app_id: str,
    app_name: str,
    doc_name: str | None,
    default_extension: str,
    append_text: str,
) -> dict[str, Any]:
    opened = open_document(app_id=app_id, app_name=app_name, doc_name=doc_name, default_extension=default_extension)
    target = Path(str(opened["file"]))
    existing = str(opened["content"])
    appended = str(append_text or "").strip() or "edit=applied"
    updated = existing.rstrip("\n") + f"\n{appended}\n"
    target.write_text(updated, encoding="utf-8")
    state = _load_state(app_id)
    state["documents_edited"] = int(state.get("documents_edited", 0)) + 1
    state["last_edited"] = str(target)
    _save_state(app_id, state)
    return _doc_result(
        "PRODUCTIVITY_EDIT_OK",
        target,
        updated,
        app_id=app_id,
        app=app_name,
        appended=appended,
    )


def export_document(
    *,
    app_id: str,
    app_name: str,
    doc_name: str | None,
    default_extension: str,
    export_format: str | None,
    supported_exports: list[str],
) -> dict[str, Any]:
    opened = open_document(app_id=app_id, app_name=app_name, doc_name=doc_name, default_extension=default_extension)
    source = Path(str(opened["file"]))
    source_content = str(opened["content"])

    requested = str(export_format or "").strip().lower()
    export_exts = [str(x).strip().lower().lstrip(".") for x in supported_exports if str(x).strip()]
    if not export_exts:
        export_exts = [str(default_extension).lstrip(".")]
    chosen = requested.lstrip(".") if requested else export_exts[0]
    if chosen not in export_exts:
        return {
            "ok": False,
            "code": "PRODUCTIVITY_EXPORT_FORMAT_UNSUPPORTED",
            "app_id": app_id,
            "app": app_name,
            "requested_format": requested,
            "supported_formats": export_exts,
        }

    export_file = _exports_root(app_id) / f"{source.stem}.{chosen}"
    payload = {
        "app_id": app_id,
        "app": app_name,
        "source_file": source.name,
        "source_sha256": _sha256_text(source_content),
        "export_format": chosen,
        "content": source_content,
    }
    export_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    state = _load_state(app_id)
    state["documents_exported"] = int(state.get("documents_exported", 0)) + 1
    state["last_exported"] = str(export_file)
    _save_state(app_id, state)
    export_content = export_file.read_text(encoding="utf-8-sig")
    return _doc_result(
        "PRODUCTIVITY_EXPORT_OK",
        export_file,
        export_content,
        app_id=app_id,
        app=app_name,
        export_format=chosen,
        source_file=str(source),
        source_sha256=payload["source_sha256"],
        supported_formats=export_exts,
    )


def snapshot(
    *,
    app_id: str,
    app_name: str,
    replacement_for: list[str],
    engines: list[str],
    default_extension: str,
    supported_exports: list[str],
) -> dict[str, Any]:
    state = _load_state(app_id)
    out = {
        "app": app_name,
        "app_id": app_id,
        "ready": True,
        "replacement_for": list(replacement_for),
        "engines": list(engines),
        "default_extension": str(default_extension).lstrip("."),
        "supported_exports": [str(x).lstrip(".") for x in supported_exports],
        "operations": {
            "open_document": True,
            "edit_document": True,
            "export_document": True,
        },
        "state": {
            "documents_opened": int(state.get("documents_opened", 0)),
            "documents_edited": int(state.get("documents_edited", 0)),
            "documents_exported": int(state.get("documents_exported", 0)),
            "last_opened": state.get("last_opened"),
            "last_edited": state.get("last_edited"),
            "last_exported": state.get("last_exported"),
        },
        "updated_utc": _now_iso(),
    }
    _write_json(_state_path(app_id), {**state, "updated_utc": out["updated_utc"]})
    return out
