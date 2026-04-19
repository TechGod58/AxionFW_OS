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


BUS = Path(axion_path_str("runtime", "shell_ui", "event_bus"))
CP = Path(axion_path_str("runtime", "shell_ui", "control_panel_host"))
WT = Path(axion_path_str("runtime", "shell_ui", "windows_tools_host"))
if str(BUS) not in sys.path:
    sys.path.append(str(BUS))
if str(CP) not in sys.path:
    sys.path.append(str(CP))
if str(WT) not in sys.path:
    sys.path.append(str(WT))

from event_bus import publish
from control_panel_host import invoke_item_action, open_item as control_panel_open_item, get_item_version as control_panel_get_item_version, list_item_versions as control_panel_list_item_versions
from windows_tools_host import (
    open_tool as windows_tools_open_tool,
    launch_tool as windows_tools_launch_tool,
    invoke_tool_action as windows_tools_invoke_tool_action,
    get_tool_version as windows_tools_get_tool_version,
    list_tools as windows_tools_list_tools,
    list_tool_versions as windows_tools_list_tool_versions,
    get_tool_contract as windows_tools_get_tool_contract,
)


def _wrap_dispatch(host_name: str, action: str, item: str | None, result: dict, corr: str | None):
    out = {
        "ok": bool(result.get("ok")),
        "code": "UI_ACTION_DISPATCHED" if bool(result.get("ok")) else "UI_ACTION_FAILED",
        "host": host_name,
        "item": item,
        "action": action,
        "result": result,
    }
    publish("shell.ui.action.dispatched", out, corr=corr, source="shell_action_contract")
    return out


def _fail(host: str, action: str, code: str, corr: str | None, extra: dict | None = None):
    out = {"ok": False, "code": code, "host": host, "action": action}
    if isinstance(extra, dict):
        out.update(extra)
    publish("shell.ui.action.failed", out, corr=corr, source="shell_action_contract")
    return out


def dispatch_ui_action(host: str, action: str, item: str = None, args: dict | None = None, corr: str = None):
    target = str(host or "").strip().lower()
    normalized_action = str(action or "").strip().lower()
    payload = args or {}

    if target in ("control_panel", "control_panel_host"):
        if normalized_action == "list_item_versions":
            result = control_panel_list_item_versions(category=payload.get("category"))
            return _wrap_dispatch("control_panel_host", normalized_action, item, result, corr)

        if normalized_action == "get_item_version":
            item_name = str(payload.get("item") or item or "").strip()
            if not item_name:
                return _fail("control_panel_host", normalized_action, "UI_ACTION_ITEM_REQUIRED", corr)
            result = control_panel_get_item_version(item_name)
            return _wrap_dispatch("control_panel_host", normalized_action, item_name, result, corr)

        if normalized_action == "open_item":
            item_name = str(payload.get("item") or item or "").strip()
            if not item_name:
                return _fail("control_panel_host", normalized_action, "UI_ACTION_ITEM_REQUIRED", corr)
            result = control_panel_open_item(item_name, corr=corr)
            return _wrap_dispatch("control_panel_host", normalized_action, item_name, result, corr)

        if not item:
            return _fail("control_panel_host", normalized_action, "UI_ACTION_ITEM_REQUIRED", corr)
        result = invoke_item_action(item, normalized_action, payload=payload, corr=corr)
        return _wrap_dispatch("control_panel_host", normalized_action, item, result, corr)

    if target in ("windows_tools", "windows_tools_host"):
        if normalized_action == "list_tools":
            result = windows_tools_list_tools(group=payload.get("group"))
            return _wrap_dispatch("windows_tools_host", normalized_action, item, result, corr)

        if normalized_action == "list_tool_versions":
            result = windows_tools_list_tool_versions(group=payload.get("group"))
            return _wrap_dispatch("windows_tools_host", normalized_action, item, result, corr)

        if normalized_action == "get_tool_version":
            tool_id = str(payload.get("tool_id") or item or "").strip()
            if not tool_id:
                return _fail("windows_tools_host", normalized_action, "UI_ACTION_ITEM_REQUIRED", corr)
            result = windows_tools_get_tool_version(tool_id)
            return _wrap_dispatch("windows_tools_host", normalized_action, tool_id, result, corr)

        if normalized_action == "get_tool_contract":
            tool_id = str(payload.get("tool_id") or item or "").strip()
            if not tool_id:
                return _fail("windows_tools_host", normalized_action, "UI_ACTION_ITEM_REQUIRED", corr)
            result = windows_tools_get_tool_contract(tool_id)
            return _wrap_dispatch("windows_tools_host", normalized_action, tool_id, result, corr)

        if normalized_action == "launch_tool":
            tool_id = str(payload.get("tool_id") or item or "").strip()
            if not tool_id:
                return _fail("windows_tools_host", normalized_action, "UI_ACTION_ITEM_REQUIRED", corr)
            result = windows_tools_launch_tool(
                tool_id,
                corr=corr or "corr_windows_tools_contract_launch_001",
                family=payload.get("family"),
                profile=payload.get("profile"),
                expected_flow_profile=payload.get("expected_flow_profile"),
                traffic_sample=payload.get("traffic_sample"),
            )
            return _wrap_dispatch("windows_tools_host", normalized_action, tool_id, result, corr)

        if normalized_action in (
            "smart_driver_fabric_status",
            "smart_driver_fabric_compile",
            "smart_driver_fabric_kernel_handoff",
            "smart_driver_fabric_refresh",
            "smart_driver_builder_snapshot",
            "smart_driver_builder_submit_issues",
            "smart_driver_builder_rebuild",
            "stage_bios_settings",
            "get_pending_bios_settings",
        ):
            if normalized_action in ("stage_bios_settings", "get_pending_bios_settings"):
                default_tool = "firmware_bios_settings"
            elif normalized_action.startswith("smart_driver_builder_"):
                default_tool = "smart_driver_builder"
            else:
                default_tool = "smart_driver_fabric"
            tool_id = str(payload.get("tool_id") or item or default_tool).strip()
            result = windows_tools_invoke_tool_action(tool_id, normalized_action, payload=payload, corr=corr or "corr_windows_tools_action_contract_001")
            return _wrap_dispatch("windows_tools_host", normalized_action, tool_id, result, corr)

        tool_id = str(payload.get("tool_id") or item or "").strip()
        if not tool_id:
            return _fail("windows_tools_host", normalized_action, "UI_ACTION_ITEM_REQUIRED", corr)
        result = windows_tools_open_tool(tool_id, corr=corr)
        return _wrap_dispatch("windows_tools_host", normalized_action, tool_id, result, corr)

    return _fail(target, normalized_action, "UI_ACTION_HOST_UNKNOWN", corr, extra={"host": host})
