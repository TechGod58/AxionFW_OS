import sys
from pathlib import Path

from shell_action_contract import dispatch_ui_action

APPS_HOST_DIR = Path(__file__).resolve().parents[1] / "apps_host"
if str(APPS_HOST_DIR) not in sys.path:
    sys.path.append(str(APPS_HOST_DIR))

from apps_host import build_installer_provenance_envelope


def test_dispatch_unknown_host():
    out = dispatch_ui_action("unknown_host", "run_installer", item="Programs and Features", args={})
    assert out["ok"] is False
    assert out["code"] == "UI_ACTION_HOST_UNKNOWN"


def test_dispatch_control_panel_installer():
    provenance = build_installer_provenance_envelope(
        "contract_setup.msi",
        family="windows",
        profile="win95",
        source_commit_sha="0505050505050505050505050505050505050505",
        build_pipeline_id="axion-test-action-contract",
    )
    out = dispatch_ui_action(
        "control_panel",
        "run_installer",
        item="Programs and Features",
        args={
            "installer_path": "contract_setup.msi",
            "family": "windows",
            "profile": "win95",
            "execute": True,
            "provenance": provenance,
        },
        corr="corr_action_contract_001",
    )
    assert out["ok"] is True
    assert out["code"] == "UI_ACTION_DISPATCHED"
    assert out["result"]["result"]["code"] == "LAUNCH_INSTALLER_EXECUTED"


def test_dispatch_control_panel_versions():
    listed = dispatch_ui_action("control_panel", "list_item_versions", args={"category": "Windows Tools and Media"}, corr="corr_action_contract_001b")
    assert listed["ok"] is True
    assert listed["result"]["code"] == "CONTROL_PANEL_VERSIONS_OK"
    assert any(item["id"] == "command_prompt" for item in listed["result"]["items"])

    item_version = dispatch_ui_action("control_panel", "get_item_version", item="command_prompt", args={}, corr="corr_action_contract_001c")
    assert item_version["ok"] is True
    assert item_version["result"]["code"] == "CONTROL_PANEL_ITEM_VERSION_OK"


def test_dispatch_control_panel_launch_item():
    launched = dispatch_ui_action("control_panel", "launch_item", item="Command Prompt", args={}, corr="corr_action_contract_001d")
    assert launched["ok"] is True
    assert launched["result"]["result"]["code"] in ("WINDOWS_TOOLS_LAUNCH_OK", "CONTROL_PANEL_ITEM_LAUNCH_OK")


def test_dispatch_windows_tools_open_and_version():
    opened = dispatch_ui_action("windows_tools", "open_tool", item="event_viewer", args={}, corr="corr_action_contract_002")
    assert opened["ok"] is True
    assert opened["host"] == "windows_tools_host"
    assert opened["result"]["code"] == "WINDOWS_TOOLS_ITEM_OPEN_OK"

    versioned = dispatch_ui_action("windows_tools", "get_tool_version", item="event_viewer", args={}, corr="corr_action_contract_003")
    assert versioned["ok"] is True
    assert versioned["result"]["code"] == "WINDOWS_TOOLS_VERSION_OK"
    assert versioned["result"]["version"].startswith("axion-event-viewer-")


def test_dispatch_windows_tools_contract_and_versions():
    contract = dispatch_ui_action("windows_tools", "get_tool_contract", item="resource_monitor", args={}, corr="corr_action_contract_004")
    assert contract["ok"] is True
    assert contract["result"]["code"] == "WINDOWS_TOOLS_CONTRACT_OK"

    listed = dispatch_ui_action("windows_tools", "list_tool_versions", args={"group": "Diagnostics"}, corr="corr_action_contract_005")
    assert listed["ok"] is True
    assert listed["result"]["code"] == "WINDOWS_TOOLS_VERSIONS_OK"
    assert any(item["tool_id"] == "resource_monitor" for item in listed["result"]["items"])


def test_dispatch_windows_tools_launch_tool():
    launched = dispatch_ui_action("windows_tools", "launch_tool", item="powershell", args={}, corr="corr_action_contract_006")
    assert launched["ok"] is True
    assert launched["result"]["code"] == "WINDOWS_TOOLS_LAUNCH_OK"
    assert launched["result"]["result"]["code"] == "LAUNCH_OK"


def test_dispatch_windows_tools_smart_driver_fabric_actions():
    status = dispatch_ui_action(
        "windows_tools",
        "smart_driver_fabric_status",
        item="smart_driver_fabric",
        args={},
        corr="corr_action_contract_007",
    )
    assert status["ok"] is True
    assert status["result"]["code"] == "WINDOWS_TOOLS_ACTION_OK"
    assert status["result"]["result"]["code"] in ("SMART_DRIVER_FABRIC_READY", "SMART_DRIVER_FABRIC_REUSED")

    handoff = dispatch_ui_action(
        "windows_tools",
        "smart_driver_fabric_kernel_handoff",
        item="smart_driver_fabric",
        args={},
        corr="corr_action_contract_008",
    )
    assert handoff["ok"] is True
    assert handoff["result"]["code"] == "WINDOWS_TOOLS_ACTION_OK"
    assert handoff["result"]["result"]["code"] == "SMART_DRIVER_KERNEL_HANDOFF_READY"


def test_dispatch_windows_tools_smart_driver_builder_actions():
    snap = dispatch_ui_action(
        "windows_tools",
        "smart_driver_builder_snapshot",
        item="smart_driver_builder",
        args={},
        corr="corr_action_contract_008b",
    )
    assert snap["ok"] is True
    assert snap["result"]["code"] == "WINDOWS_TOOLS_ACTION_OK"
    assert snap["result"]["result"]["code"] == "SMART_DRIVER_BUILDER_SNAPSHOT_OK"

    submitted = dispatch_ui_action(
        "windows_tools",
        "smart_driver_builder_submit_issues",
        item="smart_driver_builder",
        args={
            "issues": [
                {"summary": "GPU timeout spike under load", "frequency": "intermittent"},
                "Camera driver delayed initialize",
            ],
            "reporter": "action_contract_test",
            "device_context": {"board_family": "q35_ovmf_ref"},
        },
        corr="corr_action_contract_008c",
    )
    assert submitted["ok"] is True
    assert submitted["result"]["code"] == "WINDOWS_TOOLS_ACTION_OK"
    assert submitted["result"]["result"]["code"] == "SMART_DRIVER_BUILDER_ISSUES_CAPTURED"
    report_id = submitted["result"]["result"]["report"]["report_id"]

    rebuilt = dispatch_ui_action(
        "windows_tools",
        "smart_driver_builder_rebuild",
        item="smart_driver_builder",
        args={"report_id": report_id, "force_rebuild": True, "build_handoff": True},
        corr="corr_action_contract_008d",
    )
    assert rebuilt["ok"] is True
    assert rebuilt["result"]["code"] == "WINDOWS_TOOLS_ACTION_OK"
    assert rebuilt["result"]["result"]["code"] == "SMART_DRIVER_BUILDER_REBUILD_OK"


def test_dispatch_windows_tools_firmware_bios_settings_actions():
    staged = dispatch_ui_action(
        "windows_tools",
        "stage_bios_settings",
        item="firmware_bios_settings",
        args={
            "settings": {
                "virtualization": True,
                "iommu": True,
                "secure_boot_mode": "standard",
            },
            "actor": "action_contract_test",
        },
        corr="corr_action_contract_009",
    )
    assert staged["ok"] is True
    assert staged["result"]["code"] == "WINDOWS_TOOLS_ACTION_OK"
    assert staged["result"]["result"]["code"] == "BIOS_SETTINGS_STAGED_PENDING_RESTART"

    pending = dispatch_ui_action(
        "windows_tools",
        "get_pending_bios_settings",
        item="firmware_bios_settings",
        args={},
        corr="corr_action_contract_010",
    )
    assert pending["ok"] is True
    assert pending["result"]["code"] == "WINDOWS_TOOLS_ACTION_OK"
    assert pending["result"]["result"]["code"] in ("BIOS_SETTINGS_PENDING_FOUND", "BIOS_SETTINGS_NONE_PENDING")
