from windows_tools_host import (
    snapshot,
    list_tools,
    open_tool,
    get_tool_version,
    get_tool_contract,
    list_tool_versions,
    launch_tool,
    invoke_tool_action,
)


def test_windows_tools_snapshot_and_group_listing():
    snap = snapshot("corr_wintools_test_001")
    assert snap["title"] == "Windows Tools"
    assert snap["implementationVersion"].startswith("axion-wintools-")
    listed = list_tools("System Management")
    assert listed["ok"] is True
    assert any(x["tool_id"] == "computer_management" for x in listed["items"])


def test_windows_tools_open_and_version():
    opened = open_tool("event_viewer", corr="corr_wintools_test_002")
    assert opened["ok"] is True
    assert opened["route"] == "/computer-management"
    assert opened["resolved_host"] == "computer_management_host"

    ver = get_tool_version("event_viewer")
    assert ver["ok"] is True
    assert ver["version"].startswith("axion-event-viewer-")


def test_windows_tools_contract_and_version_listing():
    contract = get_tool_contract("resource_monitor")
    assert contract["ok"] is True
    assert contract["code"] == "WINDOWS_TOOLS_CONTRACT_OK"
    assert contract["resolved_host"] == "statistics_host"

    versions = list_tool_versions(group="Diagnostics")
    assert versions["ok"] is True
    assert any(x["tool_id"] == "resource_monitor" for x in versions["items"])


def test_windows_tools_launch_runtime_adapter():
    contract = get_tool_contract("command_prompt")
    assert contract["ok"] is True
    assert contract["launch_supported"] is True
    assert contract["launch_app_id"] == "command_prompt"

    launched = launch_tool("command_prompt", corr="corr_wintools_launch_001")
    assert launched["ok"] is True
    assert launched["code"] == "WINDOWS_TOOLS_LAUNCH_OK"
    assert launched["app_id"] == "command_prompt"
    assert launched["result"]["code"] == "LAUNCH_OK"


def test_windows_tools_launch_new_runtime_apps():
    for tool_id in (
        "task_manager",
        "services",
        "file_explorer",
        "codex",
        "write",
        "sheets",
        "slides",
        "mail",
        "database",
        "publisher",
        "pdf_studio",
        "vector_studio",
        "creative_studio",
        "notepad_plus_plus",
        "calculator",
    ):
        contract = get_tool_contract(tool_id)
        assert contract["ok"] is True
        assert contract["launch_supported"] is True
        launched = launch_tool(tool_id, corr=f"corr_wintools_launch_new_{tool_id}_001")
        assert launched["ok"] is True
        assert launched["code"] == "WINDOWS_TOOLS_LAUNCH_OK"
        assert launched["result"]["code"] == "LAUNCH_OK"


def test_windows_tools_smart_driver_fabric_actions():
    contract = get_tool_contract("smart_driver_fabric")
    assert contract["ok"] is True
    assert contract["code"] == "WINDOWS_TOOLS_CONTRACT_OK"

    status = invoke_tool_action("smart_driver_fabric", "smart_driver_fabric_status", {}, corr="corr_wintools_sdf_status_001")
    assert status["ok"] is True
    assert status["code"] == "WINDOWS_TOOLS_ACTION_OK"
    assert status["result"]["code"] in ("SMART_DRIVER_FABRIC_READY", "SMART_DRIVER_FABRIC_REUSED")

    handoff = invoke_tool_action("smart_driver_fabric", "smart_driver_fabric_kernel_handoff", {}, corr="corr_wintools_sdf_handoff_001")
    assert handoff["ok"] is True
    assert handoff["result"]["code"] == "SMART_DRIVER_KERNEL_HANDOFF_READY"


def test_windows_tools_smart_driver_builder_actions():
    contract = get_tool_contract("smart_driver_builder")
    assert contract["ok"] is True
    assert contract["code"] == "WINDOWS_TOOLS_CONTRACT_OK"

    snap = invoke_tool_action("smart_driver_builder", "smart_driver_builder_snapshot", {}, corr="corr_wintools_sdb_snapshot_001")
    assert snap["ok"] is True
    assert snap["result"]["code"] == "SMART_DRIVER_BUILDER_SNAPSHOT_OK"
    assert snap["result"]["title"] == "Smart Driver Builder"

    submitted = invoke_tool_action(
        "smart_driver_builder",
        "smart_driver_builder_submit_issues",
        {
            "issues": [
                {"summary": "Intermittent network drop under load", "frequency": "intermittent"},
                "Audio crackle after resume from sleep",
            ],
            "reporter": "windows_tools_test",
            "device_context": {"board_family": "q35_ovmf_ref"},
        },
        corr="corr_wintools_sdb_submit_001",
    )
    assert submitted["ok"] is True
    assert submitted["result"]["code"] == "SMART_DRIVER_BUILDER_ISSUES_CAPTURED"
    report_id = submitted["result"]["report"]["report_id"]

    rebuilt = invoke_tool_action(
        "smart_driver_builder",
        "smart_driver_builder_rebuild",
        {"report_id": report_id, "force_rebuild": True, "build_handoff": True},
        corr="corr_wintools_sdb_rebuild_001",
    )
    assert rebuilt["ok"] is True
    assert rebuilt["result"]["code"] == "SMART_DRIVER_BUILDER_REBUILD_OK"
    assert (rebuilt["result"].get("kernel_handoff") or {}).get("code") == "SMART_DRIVER_KERNEL_HANDOFF_READY"


def test_windows_tools_firmware_bios_settings_actions():
    contract = get_tool_contract("firmware_bios_settings")
    assert contract["ok"] is True
    assert contract["launch_supported"] is False

    staged = invoke_tool_action(
        "firmware_bios_settings",
        "stage_bios_settings",
        {
            "settings": {
                "virtualization": True,
                "iommu": True,
                "secure_boot_mode": "standard",
            },
            "actor": "windows_tools_test",
        },
        corr="corr_wintools_bios_stage_001",
    )
    assert staged["ok"] is True
    assert staged["result"]["code"] == "BIOS_SETTINGS_STAGED_PENDING_RESTART"

    pending = invoke_tool_action(
        "firmware_bios_settings",
        "get_pending_bios_settings",
        {},
        corr="corr_wintools_bios_pending_001",
    )
    assert pending["ok"] is True
    assert pending["result"]["code"] in ("BIOS_SETTINGS_PENDING_FOUND", "BIOS_SETTINGS_NONE_PENDING")


def test_windows_tools_runtime_operation_actions():
    opened = invoke_tool_action(
        "slides",
        "runtime_operation",
        {"operation": "open_document", "args": {"doc_name": "wintools_slides"}},
        corr="corr_wintools_runtime_open_001",
    )
    assert opened["ok"] is True
    assert opened["result"]["code"] == "APP_OPERATION_OK"

    edited = invoke_tool_action(
        "slides",
        "runtime_operation",
        {"operation": "edit_document", "args": {"doc_name": "wintools_slides", "append_text": "agenda=launch"}},
        corr="corr_wintools_runtime_edit_001",
    )
    assert edited["ok"] is True
    assert edited["result"]["code"] == "APP_OPERATION_OK"

    exported = invoke_tool_action(
        "slides",
        "runtime_operation",
        {"operation": "export_document", "args": {"doc_name": "wintools_slides", "export_format": "pdf"}},
        corr="corr_wintools_runtime_export_001",
    )
    assert exported["ok"] is True
    assert exported["result"]["code"] == "APP_OPERATION_OK"
