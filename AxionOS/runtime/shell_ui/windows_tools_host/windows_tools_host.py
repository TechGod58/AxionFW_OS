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


import json
from datetime import datetime, timezone

BUS = Path(axion_path_str("runtime", "shell_ui", "event_bus"))
ROUTER = Path(axion_path_str("runtime", "shell_ui", "router_host"))
LAUNCHER = Path(axion_path_str("runtime", "capsule", "launchers"))
DEVICE_FABRIC_DIR = Path(axion_path_str("runtime", "device_fabric"))
SMART_DRIVER_BUILDER_HOST_DIR = Path(axion_path_str("runtime", "shell_ui", "smart_driver_builder_host"))
FIRMWARE_RUNTIME_DIR = Path(axion_path_str("runtime", "firmware"))
KERNEL_TOOLS_DIR = Path(axion_path_str("tools", "kernel"))
if str(BUS) not in sys.path:
    sys.path.append(str(BUS))
if str(ROUTER) not in sys.path:
    sys.path.append(str(ROUTER))
if str(LAUNCHER) not in sys.path:
    sys.path.append(str(LAUNCHER))
if str(DEVICE_FABRIC_DIR) not in sys.path:
    sys.path.append(str(DEVICE_FABRIC_DIR))
if str(SMART_DRIVER_BUILDER_HOST_DIR) not in sys.path:
    sys.path.append(str(SMART_DRIVER_BUILDER_HOST_DIR))
if str(FIRMWARE_RUNTIME_DIR) not in sys.path:
    sys.path.append(str(FIRMWARE_RUNTIME_DIR))
if str(KERNEL_TOOLS_DIR) not in sys.path:
    sys.path.append(str(KERNEL_TOOLS_DIR))

from event_bus import publish
from router_host import resolve as resolve_route
from app_runtime_launcher import launch as launch_runtime, invoke_app_operation
from smart_driver_fabric import ensure_fabric_initialized
from generate_smart_driver_handoff import generate_smart_driver_handoff
from smart_driver_builder_host import (
    snapshot as smart_driver_builder_snapshot,
    submit_issue_report as smart_driver_builder_submit_issue_report,
    rebuild_from_issue_report as smart_driver_builder_rebuild_from_issue_report,
)
from bios_settings_bridge import stage_bios_settings, get_pending_bios_settings

STATE_PATH = Path(axion_path_str("config", "WINDOWS_TOOLS_STATE_V1.json"))
LAUNCH_MAP_PATH = Path(axion_path_str("config", "WINDOWS_TOOLS_LAUNCH_MAP_V1.json"))
SMART_DRIVER_TOOL_IDS = {"smart_driver_fabric", "smart_driver_builder"}
FIRMWARE_BIOS_TOOL_ID = "firmware_bios_settings"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_launch_map():
    if not LAUNCH_MAP_PATH.exists():
        return {
            "default": {"launch_mode": "app_runtime", "allow_prepare_only": True},
            "tool_launch": {},
        }
    return json.loads(LAUNCH_MAP_PATH.read_text(encoding="utf-8-sig"))


def _normalize_item(item: dict):
    tool_id = str(item.get("tool_id", "")).strip()
    if not tool_id:
        return None
    out = dict(item)
    if not str(out.get("label", "")).strip():
        out["label"] = tool_id
    if not str(out.get("route", "")).strip():
        out["route"] = "/apps"
    if not str(out.get("source", "")).strip():
        out["source"] = "windows"
    if not str(out.get("version", "")).strip():
        out["version"] = f"axion-{tool_id}-1.0.0"
    return out


def _load():
    s = json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))
    items = [_normalize_item(dict(x)) for x in s.get("items", []) if isinstance(x, dict)]
    s["items"] = [x for x in items if x is not None]
    s["implementationVersion"] = str(s.get("implementationVersion", "")).strip() or "axion-wintools-1.0.0"
    return s


def _resolve_launch_spec(item: dict):
    launch_map = _load_launch_map()
    tool_id = str(item.get("tool_id", "")).strip()
    defaults = launch_map.get("default", {}) if isinstance(launch_map, dict) else {}
    spec = ((launch_map.get("tool_launch", {}) if isinstance(launch_map, dict) else {}).get(tool_id, {}))
    if not isinstance(spec, dict):
        spec = {}
    app_id = str(spec.get("app_id", "")).strip() or None
    expected_flow_profile = spec.get("expected_flow_profile")
    launch_mode = str(spec.get("launch_mode", defaults.get("launch_mode", "app_runtime"))).strip() or "app_runtime"
    allow_prepare_only = bool(spec.get("allow_prepare_only", defaults.get("allow_prepare_only", True)))
    return {
        "app_id": app_id,
        "launch_mode": launch_mode,
        "allow_prepare_only": allow_prepare_only,
        "expected_flow_profile": expected_flow_profile,
    }


def _resolve_item(item: dict):
    route = str(item.get("route", "")).strip()
    route_result = resolve_route(route, corr="corr_windows_tools_route_resolve") if route else {"ok": False, "code": "ROUTE_EMPTY", "route": route}
    host = str(item.get("target", "")).strip() or str(route_result.get("host", "")).strip() or None
    launch_spec = _resolve_launch_spec(item)
    out = dict(item)
    out["route_ok"] = bool(route_result.get("ok"))
    out["resolved_host"] = host
    out["route_result"] = route_result
    out["launch_app_id"] = launch_spec.get("app_id")
    out["launch_mode"] = launch_spec.get("launch_mode")
    out["allow_prepare_only"] = bool(launch_spec.get("allow_prepare_only", True))
    out["expected_flow_profile"] = launch_spec.get("expected_flow_profile")
    out["launch_supported"] = bool(launch_spec.get("app_id")) and str(launch_spec.get("launch_mode")) == "app_runtime"
    return out


def snapshot(corr="corr_windows_tools_001"):
    s = _load()
    resolved = [_resolve_item(item) for item in s.get("items", []) if isinstance(item, dict)]
    versions = {str(item.get("tool_id")): str(item.get("version", "")) for item in resolved}
    out = {"ts": _now(), "corr": corr, "toolVersions": versions, **s, "items": resolved}
    publish("shell.windows_tools.refreshed", {"ok": True}, corr=corr, source="windows_tools_host")
    return out


def list_tools(group: str | None = None):
    s = _load()
    items = [dict(x) for x in s.get("items", []) if isinstance(x, dict)]
    g = str(group or "").strip().lower()
    if not g:
        return {"ok": True, "code": "WINDOWS_TOOLS_LIST_OK", "items": items}
    valid = set()
    for grp in s.get("groups", []):
        if str(grp.get("name", "")).strip().lower() == g:
            for tool_id in grp.get("items", []):
                valid.add(str(tool_id))
    filtered = [x for x in items if str(x.get("tool_id")) in valid]
    return {"ok": True, "code": "WINDOWS_TOOLS_LIST_OK", "items": filtered}


def list_tool_versions(group: str | None = None):
    listed = list_tools(group=group)
    items = [
        {
            "tool_id": str(item.get("tool_id")),
            "label": str(item.get("label", "")),
            "version": str(item.get("version", "")),
            "route": str(item.get("route", "")),
            "target": str(item.get("target", "")),
        }
        for item in listed.get("items", [])
    ]
    return {"ok": True, "code": "WINDOWS_TOOLS_VERSIONS_OK", "items": items}


def _find_tool(tool_id: str):
    s = _load()
    for item in s.get("items", []):
        if str(item.get("tool_id")) == str(tool_id):
            return item
    return None


def get_tool_contract(tool_id: str):
    item = _find_tool(tool_id)
    if item is None:
        return {"ok": False, "code": "WINDOWS_TOOLS_ITEM_UNKNOWN", "tool_id": str(tool_id)}
    resolved = _resolve_item(item)
    return {
        "ok": bool(resolved.get("route_ok")),
        "code": "WINDOWS_TOOLS_CONTRACT_OK" if bool(resolved.get("route_ok")) else "WINDOWS_TOOLS_ROUTE_UNRESOLVED",
        "tool_id": str(resolved.get("tool_id")),
        "label": str(resolved.get("label", "")),
        "version": str(resolved.get("version", "")),
        "route": str(resolved.get("route", "")),
        "target": str(resolved.get("target", "")),
        "resolved_host": resolved.get("resolved_host"),
        "route_result": resolved.get("route_result"),
        "launch_supported": bool(resolved.get("launch_supported", False)),
        "launch_app_id": resolved.get("launch_app_id"),
        "launch_mode": resolved.get("launch_mode"),
        "allow_prepare_only": bool(resolved.get("allow_prepare_only", True)),
        "expected_flow_profile": resolved.get("expected_flow_profile"),
    }


def open_tool(tool_id: str, corr="corr_windows_tools_open_001"):
    contract = get_tool_contract(tool_id)
    if not bool(contract.get("ok")):
        if contract.get("code") == "WINDOWS_TOOLS_ITEM_UNKNOWN":
            return {"ok": False, "code": "WINDOWS_TOOLS_ITEM_UNKNOWN", "tool_id": str(tool_id)}
        return {
            "ok": False,
            "code": "WINDOWS_TOOLS_ROUTE_UNRESOLVED",
            "tool_id": str(tool_id),
            "route": contract.get("route"),
            "route_result": contract.get("route_result"),
        }
    out = {
        "ok": True,
        "code": "WINDOWS_TOOLS_ITEM_OPEN_OK",
        "tool_id": contract.get("tool_id"),
        "label": contract.get("label"),
        "version": contract.get("version"),
        "route": contract.get("route"),
        "target": contract.get("target"),
        "resolved_host": contract.get("resolved_host"),
        "launch_supported": bool(contract.get("launch_supported", False)),
        "launch_app_id": contract.get("launch_app_id"),
    }
    publish(
        "shell.windows_tools.item.opened",
        {
            "tool_id": str(tool_id),
            "route": contract.get("route"),
            "version": contract.get("version"),
            "resolved_host": contract.get("resolved_host"),
            "launch_app_id": contract.get("launch_app_id"),
        },
        corr=corr,
        source="windows_tools_host",
    )
    return out


def launch_tool(
    tool_id: str,
    corr: str = "corr_windows_tools_launch_001",
    *,
    family: str | None = None,
    profile: str | None = None,
    expected_flow_profile: str | None = None,
    traffic_sample: list[dict] | None = None,
):
    contract = get_tool_contract(tool_id)
    if not bool(contract.get("ok")):
        return {
            "ok": False,
            "code": str(contract.get("code")),
            "tool_id": str(tool_id),
            "contract": contract,
        }
    app_id = str(contract.get("launch_app_id") or "").strip()
    if not app_id or str(contract.get("launch_mode")) != "app_runtime":
        return {
            "ok": False,
            "code": "WINDOWS_TOOLS_LAUNCH_NOT_SUPPORTED",
            "tool_id": str(tool_id),
            "contract": contract,
        }

    flow_profile = expected_flow_profile
    if flow_profile is None:
        flow_profile = contract.get("expected_flow_profile")

    result = launch_runtime(
        app_id,
        corr=corr,
        family=family,
        profile=profile,
        expected_flow_profile=flow_profile,
        traffic_sample=traffic_sample,
    )
    ok = bool(result.get("ok"))
    out = {
        "ok": ok,
        "code": "WINDOWS_TOOLS_LAUNCH_OK" if ok else "WINDOWS_TOOLS_LAUNCH_FAIL",
        "tool_id": str(tool_id),
        "app_id": app_id,
        "contract": contract,
        "result": result,
    }
    publish(
        "shell.windows_tools.item.launched",
        {
            "tool_id": str(tool_id),
            "app_id": app_id,
            "ok": ok,
            "launch_code": result.get("code"),
        },
        corr=corr,
        source="windows_tools_host",
    )
    return out


def invoke_tool_action(tool_id: str, action: str, payload: dict | None = None, corr: str = "corr_windows_tools_action_001"):
    item = _find_tool(tool_id)
    if item is None:
        return {"ok": False, "code": "WINDOWS_TOOLS_ITEM_UNKNOWN", "tool_id": str(tool_id)}
    payload = payload or {}
    normalized = str(action or "").strip().lower()
    t_id = str(item.get("tool_id", "")).strip()
    if normalized in ("runtime_operation", "app_operation"):
        op_name = str(payload.get("operation") or "").strip()
        app_id = str((_resolve_launch_spec(item) or {}).get("app_id") or "").strip()
        if not app_id:
            return {
                "ok": False,
                "code": "WINDOWS_TOOLS_ACTION_UNSUPPORTED",
                "tool_id": t_id,
                "action": normalized,
            }
        result = invoke_app_operation(
            app_id=app_id,
            operation=op_name,
            payload=payload.get("args") if isinstance(payload.get("args"), dict) else {},
            corr=corr,
        )
    elif t_id in SMART_DRIVER_TOOL_IDS:
        if normalized == "smart_driver_fabric_status":
            result = ensure_fabric_initialized(corr=corr, force_rebuild=False)
        elif normalized == "smart_driver_fabric_compile":
            result = ensure_fabric_initialized(corr=corr, force_rebuild=bool(payload.get("force_rebuild", False)))
        elif normalized == "smart_driver_fabric_kernel_handoff":
            result = generate_smart_driver_handoff()
        elif normalized == "smart_driver_fabric_refresh":
            status = ensure_fabric_initialized(corr=corr, force_rebuild=bool(payload.get("force_rebuild", False)))
            build_handoff = bool(payload.get("build_handoff", True))
            handoff = generate_smart_driver_handoff() if build_handoff else {"ok": True, "code": "SMART_DRIVER_KERNEL_HANDOFF_SKIPPED"}
            result = {
                "ok": bool(status.get("ok")) and bool(handoff.get("ok")),
                "code": "SMART_DRIVER_FABRIC_REFRESH_OK" if bool(status.get("ok")) and bool(handoff.get("ok")) else "SMART_DRIVER_FABRIC_REFRESH_FAIL",
                "status": status,
                "kernel_handoff": handoff,
            }
        elif normalized == "smart_driver_builder_snapshot":
            result = smart_driver_builder_snapshot(corr=corr)
        elif normalized == "smart_driver_builder_submit_issues":
            result = smart_driver_builder_submit_issue_report(
                payload.get("issues"),
                corr=corr,
                reporter=payload.get("reporter"),
                device_context=payload.get("device_context"),
            )
        elif normalized == "smart_driver_builder_rebuild":
            result = smart_driver_builder_rebuild_from_issue_report(
                report_id=payload.get("report_id"),
                corr=corr,
                force_rebuild=bool(payload.get("force_rebuild", True)),
                build_handoff=bool(payload.get("build_handoff", True)),
            )
        else:
            return {
                "ok": False,
                "code": "WINDOWS_TOOLS_ACTION_UNKNOWN",
                "tool_id": t_id,
                "action": normalized,
            }
    elif t_id == FIRMWARE_BIOS_TOOL_ID:
        if normalized == "stage_bios_settings":
            result = stage_bios_settings(
                settings=payload.get("settings") if isinstance(payload.get("settings"), dict) else {},
                actor=str(payload.get("actor") or "windows_tools"),
                corr=corr,
            )
        elif normalized == "get_pending_bios_settings":
            result = get_pending_bios_settings()
        else:
            return {
                "ok": False,
                "code": "WINDOWS_TOOLS_ACTION_UNKNOWN",
                "tool_id": t_id,
                "action": normalized,
            }
    else:
        return {
            "ok": False,
            "code": "WINDOWS_TOOLS_ACTION_UNSUPPORTED",
            "tool_id": t_id,
            "action": normalized,
        }

    out = {
        "ok": bool(result.get("ok")),
        "code": "WINDOWS_TOOLS_ACTION_OK" if bool(result.get("ok")) else "WINDOWS_TOOLS_ACTION_FAIL",
        "tool_id": t_id,
        "action": normalized,
        "result": result,
    }
    publish(
        "shell.windows_tools.item.action.executed",
        {
            "tool_id": t_id,
            "action": normalized,
            "ok": bool(out.get("ok")),
            "result_code": result.get("code"),
        },
        corr=corr,
        source="windows_tools_host",
    )
    return out


def get_tool_version(tool_id: str):
    out = get_tool_contract(tool_id)
    if not bool(out.get("ok")):
        return {
            "ok": False,
            "code": out.get("code"),
            "tool_id": str(tool_id),
            "route": out.get("route"),
            "route_result": out.get("route_result"),
        }
    return {
        "ok": True,
        "code": "WINDOWS_TOOLS_VERSION_OK",
        "tool_id": str(tool_id),
        "label": out.get("label"),
        "version": out.get("version"),
        "route": out.get("route"),
        "resolved_host": out.get("resolved_host"),
        "launch_app_id": out.get("launch_app_id"),
        "launch_supported": bool(out.get("launch_supported", False)),
    }


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
