import sys
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


import hashlib
import json
from datetime import datetime, timezone
from typing import Any

BUS = Path(axion_path_str("runtime", "shell_ui", "event_bus"))
DEVICE_FABRIC_DIR = Path(axion_path_str("runtime", "device_fabric"))
KERNEL_TOOLS_DIR = Path(axion_path_str("tools", "kernel"))
if str(BUS) not in sys.path:
    sys.path.append(str(BUS))
if str(DEVICE_FABRIC_DIR) not in sys.path:
    sys.path.append(str(DEVICE_FABRIC_DIR))
if str(KERNEL_TOOLS_DIR) not in sys.path:
    sys.path.append(str(KERNEL_TOOLS_DIR))

from event_bus import publish
from smart_driver_fabric import ensure_fabric_initialized
from generate_smart_driver_handoff import generate_smart_driver_handoff

STATE_PATH = Path(axion_path_str("config", "SMART_DRIVER_BUILDER_GUI_STATE_V1.json"))
ISSUE_LOG_PATH = Path(axion_path_str("data", "drivers", "smart_driver_builder_issue_reports.ndjson"))
SESSION_LOG_PATH = Path(axion_path_str("data", "drivers", "smart_driver_builder_rebuild_sessions.ndjson"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> dict[str, Any]:
    return {
        "version": 1,
        "title": "Smart Driver Builder",
        "style": "windows11_fabric_builder",
        "implementationVersion": "axion-smart-driver-builder-1.0.0",
        "description": "Capture driver issues and rebuild Smart Driver Fabric with guided context.",
        "issueSchema": {
            "required_fields": ["summary"],
            "optional_fields": ["symptom", "frequency", "affected_hardware", "notes"],
        },
        "actions": [
            "smart_driver_builder_snapshot",
            "smart_driver_builder_submit_issues",
            "smart_driver_builder_rebuild",
        ],
    }


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return _default_state()
    try:
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return _default_state()
    if not isinstance(raw, dict):
        return _default_state()
    out = _default_state()
    out.update(raw)
    return out


def _iter_ndjson_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        raw = str(line).strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _append_ndjson_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")


def _normalize_issue(entry: Any) -> dict[str, Any] | None:
    if isinstance(entry, str):
        summary = str(entry).strip()
        if not summary:
            return None
        return {
            "summary": summary,
            "symptom": summary,
            "frequency": "unspecified",
            "affected_hardware": [],
            "notes": None,
        }
    if isinstance(entry, dict):
        summary = str(entry.get("summary") or entry.get("symptom") or "").strip()
        if not summary:
            return None
        affected = entry.get("affected_hardware")
        if isinstance(affected, list):
            hardware = [str(x).strip() for x in affected if str(x).strip()]
        elif str(affected or "").strip():
            hardware = [str(affected).strip()]
        else:
            hardware = []
        return {
            "summary": summary,
            "symptom": str(entry.get("symptom") or summary).strip(),
            "frequency": str(entry.get("frequency") or "unspecified").strip() or "unspecified",
            "affected_hardware": hardware,
            "notes": str(entry.get("notes") or "").strip() or None,
        }
    return None


def _issue_report_id(issues: list[dict[str, Any]], corr: str) -> str:
    payload = json.dumps({"issues": issues, "corr": corr}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    token = hashlib.sha256(payload).hexdigest()[:12]
    return f"sdf_issue_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{token}"


def _recent_reports(limit: int = 10) -> list[dict[str, Any]]:
    rows = _iter_ndjson_rows(ISSUE_LOG_PATH)
    rows.sort(key=lambda x: str(x.get("captured_utc") or ""), reverse=True)
    return rows[: max(1, int(limit))]


def snapshot(corr: str = "corr_smart_driver_builder_001") -> dict[str, Any]:
    state = _load_state()
    status = ensure_fabric_initialized(corr=corr, force_rebuild=False)
    reports = _recent_reports(limit=12)
    out = {
        "ok": True,
        "code": "SMART_DRIVER_BUILDER_SNAPSHOT_OK",
        "ts": _now_iso(),
        "corr": corr,
        **state,
        "fabric_status": status,
        "recent_issue_reports": reports,
    }
    publish(
        "shell.smart_driver_builder.refreshed",
        {"ok": True, "reports": len(reports), "fabric_code": status.get("code")},
        corr=corr,
        source="smart_driver_builder_host",
    )
    return out


def submit_issue_report(
    issues: list[Any] | Any,
    *,
    corr: str = "corr_smart_driver_builder_submit_001",
    reporter: str | None = None,
    device_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = issues if isinstance(issues, list) else [issues]
    normalized: list[dict[str, Any]] = []
    for row in rows:
        parsed = _normalize_issue(row)
        if parsed is not None:
            normalized.append(parsed)
    if not normalized:
        return {
            "ok": False,
            "code": "SMART_DRIVER_BUILDER_ISSUES_MISSING",
            "corr": corr,
            "accepted_count": 0,
        }

    report_id = _issue_report_id(normalized, corr=corr)
    report = {
        "report_id": report_id,
        "captured_utc": _now_iso(),
        "corr": corr,
        "reporter": str(reporter or "interactive_user").strip(),
        "device_context": dict(device_context or {}),
        "issue_count": len(normalized),
        "issues": normalized,
    }
    _append_ndjson_row(ISSUE_LOG_PATH, report)
    out = {
        "ok": True,
        "code": "SMART_DRIVER_BUILDER_ISSUES_CAPTURED",
        "corr": corr,
        "report": report,
    }
    publish(
        "shell.smart_driver_builder.issues.captured",
        {"ok": True, "report_id": report_id, "issue_count": len(normalized)},
        corr=corr,
        source="smart_driver_builder_host",
    )
    return out


def rebuild_from_issue_report(
    *,
    report_id: str | None = None,
    corr: str = "corr_smart_driver_builder_rebuild_001",
    force_rebuild: bool = True,
    build_handoff: bool = True,
) -> dict[str, Any]:
    reports = _iter_ndjson_rows(ISSUE_LOG_PATH)
    selected: dict[str, Any] | None = None
    if report_id:
        key = str(report_id).strip()
        for row in reversed(reports):
            if str(row.get("report_id") or "").strip() == key:
                selected = row
                break
        if selected is None:
            return {
                "ok": False,
                "code": "SMART_DRIVER_BUILDER_REPORT_NOT_FOUND",
                "corr": corr,
                "report_id": key,
            }
    elif reports:
        selected = reports[-1]

    status = ensure_fabric_initialized(corr=corr, force_rebuild=bool(force_rebuild))
    handoff = generate_smart_driver_handoff() if bool(build_handoff) else {"ok": True, "code": "SMART_DRIVER_KERNEL_HANDOFF_SKIPPED"}
    ok = bool(status.get("ok")) and bool(handoff.get("ok"))
    session = {
        "session_id": f"sdf_rebuild_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "ts": _now_iso(),
        "corr": corr,
        "report_id": str((selected or {}).get("report_id") or ""),
        "force_rebuild": bool(force_rebuild),
        "build_handoff": bool(build_handoff),
        "status_code": status.get("code"),
        "handoff_code": handoff.get("code"),
        "ok": ok,
    }
    _append_ndjson_row(SESSION_LOG_PATH, session)

    out = {
        "ok": ok,
        "code": "SMART_DRIVER_BUILDER_REBUILD_OK" if ok else "SMART_DRIVER_BUILDER_REBUILD_FAIL",
        "corr": corr,
        "report": selected,
        "status": status,
        "kernel_handoff": handoff,
        "session": session,
    }
    publish(
        "shell.smart_driver_builder.rebuild.completed",
        {
            "ok": ok,
            "session_id": session.get("session_id"),
            "report_id": session.get("report_id"),
            "status_code": status.get("code"),
            "handoff_code": handoff.get("code"),
        },
        corr=corr,
        source="smart_driver_builder_host",
    )
    return out


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
