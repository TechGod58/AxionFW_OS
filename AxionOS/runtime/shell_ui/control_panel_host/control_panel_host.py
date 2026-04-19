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
APPS_HOST_DIR = Path(axion_path_str("runtime", "shell_ui", "apps_host"))
PRIVSEC_HOST_DIR = Path(axion_path_str("runtime", "shell_ui", "privacy_security_host"))
WT_HOST_DIR = Path(axion_path_str("runtime", "shell_ui", "windows_tools_host"))
SMART_DRIVER_BUILDER_HOST_DIR = Path(axion_path_str("runtime", "shell_ui", "smart_driver_builder_host"))
BACKUP_RESTORE_HOST_DIR = Path(axion_path_str("runtime", "shell_ui", "backup_restore_host"))
LAUNCHER_DIR = Path(axion_path_str("runtime", "capsule", "launchers"))
DEVICE_FABRIC_DIR = Path(axion_path_str("runtime", "device_fabric"))
FIRMWARE_RUNTIME_DIR = Path(axion_path_str("runtime", "firmware"))
KERNEL_TOOLS_DIR = Path(axion_path_str("tools", "kernel"))
if str(BUS) not in sys.path:
    sys.path.append(str(BUS))
if str(APPS_HOST_DIR) not in sys.path:
    sys.path.append(str(APPS_HOST_DIR))
if str(PRIVSEC_HOST_DIR) not in sys.path:
    sys.path.append(str(PRIVSEC_HOST_DIR))
if str(WT_HOST_DIR) not in sys.path:
    sys.path.append(str(WT_HOST_DIR))
if str(SMART_DRIVER_BUILDER_HOST_DIR) not in sys.path:
    sys.path.append(str(SMART_DRIVER_BUILDER_HOST_DIR))
if str(BACKUP_RESTORE_HOST_DIR) not in sys.path:
    sys.path.append(str(BACKUP_RESTORE_HOST_DIR))
if str(LAUNCHER_DIR) not in sys.path:
    sys.path.append(str(LAUNCHER_DIR))
if str(DEVICE_FABRIC_DIR) not in sys.path:
    sys.path.append(str(DEVICE_FABRIC_DIR))
if str(FIRMWARE_RUNTIME_DIR) not in sys.path:
    sys.path.append(str(FIRMWARE_RUNTIME_DIR))
if str(KERNEL_TOOLS_DIR) not in sys.path:
    sys.path.append(str(KERNEL_TOOLS_DIR))

from event_bus import publish
from apps_host import one_click_connect_module, one_click_connect_module_from_manifest, run_external_installer
from privacy_security_host import list_firewall_quarantine, adjudicate_firewall_quarantine, replay_firewall_quarantine
from windows_tools_host import launch_tool as windows_tools_launch_tool, invoke_tool_action as windows_tools_invoke_tool_action
from app_runtime_launcher import launch as launch_runtime
from smart_driver_fabric import ensure_fabric_initialized
from smart_driver_builder_host import (
    snapshot as smart_driver_builder_snapshot,
    submit_issue_report as smart_driver_builder_submit_issue_report,
    rebuild_from_issue_report as smart_driver_builder_rebuild_from_issue_report,
)
from generate_smart_driver_handoff import generate_smart_driver_handoff
from bios_settings_bridge import stage_bios_settings, get_pending_bios_settings
from backup_restore_host import (
    create_shadow_copy,
    list_shadow_copies,
    rollback_shadow_copy,
    run_shadow_copy_maintenance,
)

STATE_PATH = Path(axion_path_str("config", "CONTROL_PANEL_STATE_V1.json"))
ICON_THEME_PATH = Path(axion_path_str("config", "ICON_THEME_V1.json"))
WT_STATE_PATH = Path(axion_path_str("config", "WINDOWS_TOOLS_STATE_V1.json"))
WINDOWS_TOOLS_CATEGORY = "Windows Tools and Media"
SMART_DRIVER_ITEM_ID = "smart_driver_fabric"
SMART_DRIVER_ITEM_LABEL = "Smart Driver Fabric"
SMART_DRIVER_BUILDER_ITEM_ID = "smart_driver_builder"
SMART_DRIVER_BUILDER_ITEM_LABEL = "Smart Driver Builder"
FIRMWARE_BIOS_ITEM_ID = "firmware_bios_settings"
FIRMWARE_BIOS_ITEM_LABEL = "Firmware and BIOS Settings"
BACKUP_RESTORE_ITEM_ID = "backup_restore"
BACKUP_RESTORE_ITEM_LABEL = "Backup and Restore (Windows 7)"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_raw_state():
    return json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))


def _load_icons():
    return json.loads(ICON_THEME_PATH.read_text(encoding="utf-8-sig"))


def _load_windows_tools_items():
    if not WT_STATE_PATH.exists():
        return []
    data = json.loads(WT_STATE_PATH.read_text(encoding="utf-8-sig"))
    return [dict(item) for item in data.get("items", []) if isinstance(item, dict)]


def _normalize_cp_item(item: dict):
    normalized = dict(item)
    item_id = str(normalized.get("id", "")).strip()
    if not item_id:
        return None
    if not str(normalized.get("category", "")).strip():
        normalized["category"] = WINDOWS_TOOLS_CATEGORY
    if not str(normalized.get("route", "")).strip():
        normalized["route"] = "/apps"
    if not str(normalized.get("source", "")).strip():
        normalized["source"] = "axion"
    if "supportsProperties" not in normalized:
        normalized["supportsProperties"] = True
    if not str(normalized.get("implementation_version", "")).strip():
        fallback = str(normalized.get("version", "")).strip()
        normalized["implementation_version"] = fallback or f"axion-cp-{item_id}-1.0.0"
    return normalized


def _cp_item_from_windows_tool(tool: dict):
    tool_id = str(tool.get("tool_id", "")).strip()
    label = str(tool.get("label", "")).strip()
    if not tool_id or not label:
        return None
    tool_version = str(tool.get("version", "")).strip()
    return {
        "id": tool_id,
        "label": label,
        "category": WINDOWS_TOOLS_CATEGORY,
        "icon": "tools",
        "route": str(tool.get("route", "")).strip() or "/apps",
        "source": str(tool.get("source", "")).strip() or "windows",
        "supportsProperties": True,
        "implementation_version": tool_version or f"axion-cp-{tool_id}-1.0.0",
        "windows_tool_target": str(tool.get("target", "")).strip() or None,
    }


def _ensure_category(state: dict, category_name: str):
    categories = [dict(x) for x in state.get("categories", []) if isinstance(x, dict)]
    found = None
    for category in categories:
        if str(category.get("name", "")).strip() == category_name:
            found = category
            break
    if found is None:
        found = {"name": category_name, "icon": "tools", "items": []}
        categories.append(found)
    items = found.get("items")
    if not isinstance(items, list):
        found["items"] = []
    state["categories"] = categories
    return found


def _merge_windows_tools_into_control_panel(state: dict):
    windows_tools = _load_windows_tools_items()
    if not windows_tools:
        return state

    all_items = [_normalize_cp_item(dict(item)) for item in state.get("allItems", []) if isinstance(item, dict)]
    all_items = [item for item in all_items if item is not None]
    by_id = {str(item.get("id")): item for item in all_items}
    by_label = {str(item.get("label")): item for item in all_items}
    wt_category = _ensure_category(state, WINDOWS_TOOLS_CATEGORY)
    cat_items = [str(x) for x in wt_category.get("items", []) if str(x).strip()]

    for wt_item in windows_tools:
        cp_item = _cp_item_from_windows_tool(wt_item)
        if cp_item is None:
            continue
        cp_id = str(cp_item["id"])
        cp_label = str(cp_item["label"])
        existing = by_id.get(cp_id) or by_label.get(cp_label)
        if existing is None:
            all_items.append(cp_item)
            by_id[cp_id] = cp_item
            by_label[cp_label] = cp_item
            existing = cp_item
        elif not str(existing.get("implementation_version", "")).strip():
            existing["implementation_version"] = cp_item["implementation_version"]

        if cp_label not in cat_items:
            cat_items.append(cp_label)

    wt_category["items"] = cat_items
    state["allItems"] = all_items
    return state


def _normalize_state(state: dict):
    out = dict(state)
    out["implementationVersion"] = str(out.get("implementationVersion", "")).strip() or "axion-control-panel-2.0.0"
    out["itemVersionField"] = str(out.get("itemVersionField", "")).strip() or "implementation_version"
    return _merge_windows_tools_into_control_panel(out)


def _load():
    return _normalize_state(_load_raw_state())


def _item_index(state):
    return {item["label"]: item for item in state.get("allItems", [])} | {item["id"]: item for item in state.get("allItems", [])}


def snapshot(corr="corr_control_panel_001"):
    s = _load()
    icons = _load_icons()
    versions = {
        str(item.get("id")): str(item.get("implementation_version", ""))
        for item in s.get("allItems", [])
        if isinstance(item, dict)
    }
    out = {"ts": _now(), "corr": corr, **s, "itemVersions": versions, "iconTheme": icons}
    publish("shell.control_panel.refreshed", {"ok": True}, corr=corr, source="control_panel_host")
    return out


def list_all_items():
    s = _load()
    return list(s.get("allItems", []))


def list_item_versions(category: str | None = None):
    s = _load()
    all_items = [dict(item) for item in s.get("allItems", []) if isinstance(item, dict)]
    filtered = all_items
    wanted = str(category or "").strip().lower()
    if wanted:
        filtered = [item for item in all_items if str(item.get("category", "")).strip().lower() == wanted]
    versions = [
        {
            "id": str(item.get("id")),
            "label": str(item.get("label")),
            "category": str(item.get("category", "")),
            "implementation_version": str(item.get("implementation_version", "")),
            "route": str(item.get("route", "")),
        }
        for item in filtered
    ]
    return {"ok": True, "code": "CONTROL_PANEL_VERSIONS_OK", "items": versions}


def get_item_version(name: str):
    s = _load()
    item = _item_index(s).get(name)
    if not item:
        return {"ok": False, "code": "CONTROL_PANEL_ITEM_UNKNOWN"}
    return {
        "ok": True,
        "code": "CONTROL_PANEL_ITEM_VERSION_OK",
        "id": str(item.get("id")),
        "label": str(item.get("label")),
        "implementation_version": str(item.get("implementation_version", "")),
        "route": str(item.get("route", "")),
        "category": str(item.get("category", "")),
    }


def open_item(name: str, corr="corr_control_panel_open_001"):
    s = _load()
    item = _item_index(s).get(name)
    if item:
        publish(
            "shell.control_panel.item.opened",
            {
                "item": item["label"],
                "category": item.get("category"),
                "route": item.get("route"),
                "implementation_version": item.get("implementation_version"),
            },
            corr=corr,
            source="control_panel_host",
        )
        return {
            "ok": True,
            "code": "CONTROL_PANEL_ITEM_OPEN_OK",
            "id": item.get("id"),
            "item": item["label"],
            "category": item.get("category"),
            "route": item.get("route"),
            "implementation_version": item.get("implementation_version"),
        }
    return {"ok": False, "code": "CONTROL_PANEL_ITEM_UNKNOWN"}


def _launch_control_panel_item(item: dict, payload: dict, corr: str):
    item_id = str(item.get("id", "")).strip()
    if not item_id:
        return {"ok": False, "code": "CONTROL_PANEL_ITEM_UNKNOWN"}

    wt_result = windows_tools_launch_tool(
        item_id,
        corr=corr,
        family=payload.get("family"),
        profile=payload.get("profile"),
        expected_flow_profile=payload.get("expected_flow_profile"),
        traffic_sample=payload.get("traffic_sample"),
    )
    if bool(wt_result.get("ok")):
        return wt_result
    if str(wt_result.get("code")) not in (
        "WINDOWS_TOOLS_ITEM_UNKNOWN",
        "WINDOWS_TOOLS_LAUNCH_NOT_SUPPORTED",
    ):
        return wt_result

    route = str(item.get("route", "")).strip()
    app_id = str(payload.get("app_id") or item_id).strip()
    if route != "/apps" and not payload.get("app_id"):
        return {
            "ok": False,
            "code": "CONTROL_PANEL_LAUNCH_ROUTE_UNSUPPORTED",
            "id": item_id,
            "route": route,
        }

    launched = launch_runtime(
        app_id,
        corr=corr,
        family=payload.get("family"),
        profile=payload.get("profile"),
        expected_flow_profile=payload.get("expected_flow_profile"),
        traffic_sample=payload.get("traffic_sample"),
    )
    return {
        "ok": bool(launched.get("ok")),
        "code": "CONTROL_PANEL_ITEM_LAUNCH_OK" if bool(launched.get("ok")) else "CONTROL_PANEL_ITEM_LAUNCH_FAIL",
        "id": item_id,
        "app_id": app_id,
        "route": route,
        "result": launched,
    }


def invoke_item_action(name: str, action: str, payload: dict | None = None, corr="corr_control_panel_action_001"):
    s = _load()
    item = _item_index(s).get(name)
    if not item:
        return {"ok": False, "code": "CONTROL_PANEL_ITEM_UNKNOWN"}

    payload = payload or {}
    action = str(action or "").strip().lower()

    if action == "one_click_connect":
        app_id = payload.get("app_id")
        manifest_path = payload.get("manifest_path")
        provenance = payload.get("provenance")
        if manifest_path:
            result = one_click_connect_module_from_manifest(str(manifest_path), corr=corr, provenance=provenance)
        elif app_id:
            result = one_click_connect_module(str(app_id), corr=corr, provenance=provenance)
        else:
            return {"ok": False, "code": "CONTROL_PANEL_ACTION_MISSING_TARGET"}
        out = {
            "ok": bool(result.get("ok")),
            "code": "CONTROL_PANEL_ACTION_OK" if bool(result.get("ok")) else "CONTROL_PANEL_ACTION_FAIL",
            "item": item["label"],
            "action": "one_click_connect",
            "result": result,
        }
        publish("shell.control_panel.item.action.executed", out, corr=corr, source="control_panel_host")
        return out

    if action == "run_installer":
        installer_path = payload.get("installer_path")
        if not installer_path:
            return {"ok": False, "code": "CONTROL_PANEL_ACTION_MISSING_INSTALLER_PATH"}
        result = run_external_installer(
            installer_path=str(installer_path),
            family=payload.get("family"),
            profile=payload.get("profile"),
            app_id=payload.get("app_id"),
            expected_flow_profile=payload.get("expected_flow_profile"),
            traffic_sample=payload.get("traffic_sample"),
            corr=corr,
            execute=bool(payload.get("execute", True)),
            allow_live=bool(payload.get("allow_live", False)),
            provenance=payload.get("provenance"),
        )
        out = {
            "ok": bool(result.get("ok")),
            "code": "CONTROL_PANEL_ACTION_OK" if bool(result.get("ok")) else "CONTROL_PANEL_ACTION_FAIL",
            "item": item["label"],
            "action": "run_installer",
            "result": result,
        }
        publish("shell.control_panel.item.action.executed", out, corr=corr, source="control_panel_host")
        return out

    if action == "launch_item":
        result = _launch_control_panel_item(item, payload, corr=corr)
        out = {
            "ok": bool(result.get("ok")),
            "code": "CONTROL_PANEL_ACTION_OK" if bool(result.get("ok")) else "CONTROL_PANEL_ACTION_FAIL",
            "item": item["label"],
            "action": "launch_item",
            "result": result,
        }
        publish("shell.control_panel.item.action.executed", out, corr=corr, source="control_panel_host")
        return out

    if action in ("runtime_operation", "app_operation"):
        operation = str(payload.get("operation") or "").strip()
        if not operation:
            return {"ok": False, "code": "CONTROL_PANEL_ACTION_MISSING_OPERATION"}
        result = windows_tools_invoke_tool_action(
            str(item.get("id") or ""),
            "runtime_operation",
            {"operation": operation, "args": payload.get("args") if isinstance(payload.get("args"), dict) else {}},
            corr=corr,
        )
        out = {
            "ok": bool(result.get("ok")),
            "code": "CONTROL_PANEL_ACTION_OK" if bool(result.get("ok")) else "CONTROL_PANEL_ACTION_FAIL",
            "item": item["label"],
            "action": action,
            "result": result,
        }
        publish("shell.control_panel.item.action.executed", out, corr=corr, source="control_panel_host")
        return out

    if action in (
        "smart_driver_fabric_status",
        "smart_driver_fabric_compile",
        "smart_driver_fabric_kernel_handoff",
        "smart_driver_fabric_refresh",
        "smart_driver_builder_snapshot",
        "smart_driver_builder_submit_issues",
        "smart_driver_builder_rebuild",
    ):
        item_id = str(item.get("id", "")).strip()
        item_label = str(item.get("label", "")).strip()
        if (
            item_id not in (SMART_DRIVER_ITEM_ID, SMART_DRIVER_BUILDER_ITEM_ID)
            and item_label not in (SMART_DRIVER_ITEM_LABEL, SMART_DRIVER_BUILDER_ITEM_LABEL)
        ):
            return {"ok": False, "code": "CONTROL_PANEL_ACTION_ITEM_UNSUPPORTED", "action": action, "item": item_label}

        force_rebuild = bool(payload.get("force_rebuild", False))
        build_handoff = bool(payload.get("build_handoff", True))
        if action == "smart_driver_fabric_status":
            result = ensure_fabric_initialized(corr=corr, force_rebuild=False)
        elif action == "smart_driver_fabric_compile":
            result = ensure_fabric_initialized(corr=corr, force_rebuild=force_rebuild)
        elif action == "smart_driver_fabric_kernel_handoff":
            result = generate_smart_driver_handoff()
        elif action == "smart_driver_builder_snapshot":
            result = smart_driver_builder_snapshot(corr=corr)
        elif action == "smart_driver_builder_submit_issues":
            result = smart_driver_builder_submit_issue_report(
                payload.get("issues"),
                corr=corr,
                reporter=payload.get("reporter"),
                device_context=payload.get("device_context"),
            )
        elif action == "smart_driver_builder_rebuild":
            result = smart_driver_builder_rebuild_from_issue_report(
                report_id=payload.get("report_id"),
                corr=corr,
                force_rebuild=bool(payload.get("force_rebuild", True)),
                build_handoff=bool(payload.get("build_handoff", True)),
            )
        else:
            status = ensure_fabric_initialized(corr=corr, force_rebuild=force_rebuild)
            handoff = generate_smart_driver_handoff() if build_handoff else {"ok": True, "code": "SMART_DRIVER_KERNEL_HANDOFF_SKIPPED"}
            result = {
                "ok": bool(status.get("ok")) and bool(handoff.get("ok")),
                "code": "SMART_DRIVER_FABRIC_REFRESH_OK" if bool(status.get("ok")) and bool(handoff.get("ok")) else "SMART_DRIVER_FABRIC_REFRESH_FAIL",
                "status": status,
                "kernel_handoff": handoff,
            }

        out = {
            "ok": bool(result.get("ok")),
            "code": "CONTROL_PANEL_ACTION_OK" if bool(result.get("ok")) else "CONTROL_PANEL_ACTION_FAIL",
            "item": item["label"],
            "action": action,
            "result": result,
        }
        publish("shell.control_panel.item.action.executed", out, corr=corr, source="control_panel_host")
        return out

    if action in ("stage_bios_settings", "get_pending_bios_settings"):
        item_id = str(item.get("id", "")).strip()
        item_label = str(item.get("label", "")).strip()
        if item_id != FIRMWARE_BIOS_ITEM_ID and item_label != FIRMWARE_BIOS_ITEM_LABEL:
            return {"ok": False, "code": "CONTROL_PANEL_ACTION_ITEM_UNSUPPORTED", "action": action, "item": item_label}

        if action == "stage_bios_settings":
            settings = payload.get("settings")
            if not isinstance(settings, dict) or not settings:
                return {"ok": False, "code": "CONTROL_PANEL_ACTION_MISSING_BIOS_SETTINGS"}
            result = stage_bios_settings(
                settings=settings,
                actor=str(payload.get("actor") or "control_panel"),
                corr=corr,
            )
        else:
            result = get_pending_bios_settings()

        out = {
            "ok": bool(result.get("ok")),
            "code": "CONTROL_PANEL_ACTION_OK" if bool(result.get("ok")) else "CONTROL_PANEL_ACTION_FAIL",
            "item": item["label"],
            "action": action,
            "result": result,
        }
        publish("shell.control_panel.item.action.executed", out, corr=corr, source="control_panel_host")
        return out

    if action in (
        "shadow_copy_status",
        "list_shadow_copies",
        "create_shadow_copy",
        "rollback_shadow_copy",
        "run_shadow_copy_maintenance",
    ):
        item_id = str(item.get("id", "")).strip()
        item_label = str(item.get("label", "")).strip()
        if item_id != BACKUP_RESTORE_ITEM_ID and item_label != BACKUP_RESTORE_ITEM_LABEL:
            return {"ok": False, "code": "CONTROL_PANEL_ACTION_ITEM_UNSUPPORTED", "action": action, "item": item_label}

        scope_id = payload.get("scope_id")
        target_paths = payload.get("target_paths") if isinstance(payload.get("target_paths"), list) else None
        if action in ("shadow_copy_status", "list_shadow_copies"):
            result = list_shadow_copies(scope_id=scope_id)
        elif action == "create_shadow_copy":
            result = create_shadow_copy(
                reason=str(payload.get("reason") or "manual"),
                scope_id=scope_id,
                target_paths=target_paths,
            )
        elif action == "rollback_shadow_copy":
            snapshot_id = str(payload.get("snapshot_id") or "").strip()
            if not snapshot_id:
                return {"ok": False, "code": "CONTROL_PANEL_ACTION_MISSING_SNAPSHOT_ID"}
            result = rollback_shadow_copy(snapshot_id=snapshot_id, scope_id=scope_id)
        else:
            result = run_shadow_copy_maintenance(
                scope_id=scope_id,
                force=bool(payload.get("force", False)),
                now_utc=payload.get("now_utc"),
                target_paths=target_paths,
            )

        out = {
            "ok": bool(result.get("ok")),
            "code": "CONTROL_PANEL_ACTION_OK" if bool(result.get("ok")) else "CONTROL_PANEL_ACTION_FAIL",
            "item": item["label"],
            "action": action,
            "result": result,
        }
        publish("shell.control_panel.item.action.executed", out, corr=corr, source="control_panel_host")
        return out

    if action == "review_firewall_quarantine":
        result = list_firewall_quarantine(
            limit=int(payload.get("limit", 32) or 32),
            app_id=payload.get("app_id"),
            decision=payload.get("decision"),
            corr=corr,
        )
        out = {
            "ok": bool(result.get("ok")),
            "code": "CONTROL_PANEL_ACTION_OK" if bool(result.get("ok")) else "CONTROL_PANEL_ACTION_FAIL",
            "item": item["label"],
            "action": "review_firewall_quarantine",
            "result": result,
        }
        publish("shell.control_panel.item.action.executed", out, corr=corr, source="control_panel_host")
        return out

    if action in ("allow_firewall_quarantine", "dismiss_firewall_quarantine"):
        path = str(payload.get("path") or "").strip()
        if not path:
            return {"ok": False, "code": "CONTROL_PANEL_ACTION_MISSING_QUARANTINE_PATH"}
        decision = "allow_rule" if action == "allow_firewall_quarantine" else "dismiss"
        result = adjudicate_firewall_quarantine(
            path=path,
            decision=decision,
            note=payload.get("note"),
            corr=corr,
        )
        out = {
            "ok": bool(result.get("ok")),
            "code": "CONTROL_PANEL_ACTION_OK" if bool(result.get("ok")) else "CONTROL_PANEL_ACTION_FAIL",
            "item": item["label"],
            "action": action,
            "result": result,
        }
        publish("shell.control_panel.item.action.executed", out, corr=corr, source="control_panel_host")
        return out

    if action == "replay_firewall_quarantine":
        path = str(payload.get("path") or "").strip()
        if not path:
            return {"ok": False, "code": "CONTROL_PANEL_ACTION_MISSING_QUARANTINE_PATH"}
        result = replay_firewall_quarantine(path=path, corr=corr)
        out = {
            "ok": bool(result.get("ok")),
            "code": "CONTROL_PANEL_ACTION_OK" if bool(result.get("ok")) else "CONTROL_PANEL_ACTION_FAIL",
            "item": item["label"],
            "action": "replay_firewall_quarantine",
            "result": result,
        }
        publish("shell.control_panel.item.action.executed", out, corr=corr, source="control_panel_host")
        return out

    return {"ok": False, "code": "CONTROL_PANEL_ACTION_UNKNOWN", "action": action}


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
