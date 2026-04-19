import json
from pathlib import Path
from control_panel_host import (
    snapshot,
    open_item,
    list_all_items,
    invoke_item_action,
    get_item_version,
    list_item_versions,
)
from apps_host import (
    MODULES_INBOX_PATH,
    MODULES_CATALOG_PATH,
    MODULES_RECEIPTS_PATH,
    remove_program_module,
    build_module_provenance_envelope,
    build_installer_provenance_envelope,
)


def test_control_panel_items():
    snap = snapshot("corr_cp_test_001")
    assert snap["title"] == "ControlPanel"
    assert snap["style"] == "windows7_all_items"
    assert snap["implementationVersion"].startswith("axion-control-panel-")
    assert snap["itemVersionField"] == "implementation_version"
    assert len(snap["allItems"]) >= 40
    out = open_item("Registry Editor")
    assert out["ok"]
    assert out["implementation_version"].startswith("axion-cp-registry_editor-")


def test_control_panel_items_by_id():
    out = open_item("video_player")
    assert out["ok"]
    assert out["route"] == "/apps"
    assert any(item["id"] == "control_panel" for item in list_all_items())


def test_control_panel_windows_tools_projection_with_versions():
    all_items = list_all_items()
    labels = {item["label"] for item in all_items}
    ids = {item["id"] for item in all_items}
    assert "Command Prompt" in labels
    assert "PowerShell" in labels
    assert "command_prompt" in ids
    assert "powershell" in ids
    assert "task_manager" in ids
    assert "services" in ids
    assert "file_explorer" in ids
    assert "codex" in ids

    cmd_ver = get_item_version("command_prompt")
    assert cmd_ver["ok"] is True
    assert cmd_ver["implementation_version"].startswith("axion-")

    wt_versions = list_item_versions(category="Windows Tools and Media")
    assert wt_versions["ok"] is True
    assert any(item["id"] == "command_prompt" for item in wt_versions["items"])


def test_control_panel_launch_new_runtime_windows_tools_items():
    for name in ("Task Manager", "Services", "File Explorer", "Codex"):
        out = invoke_item_action(
            name,
            "launch_item",
            {},
            corr=f"corr_cp_launch_new_{name.replace(' ', '_').lower()}_001",
        )
        assert out["ok"] is True
        assert out["code"] == "CONTROL_PANEL_ACTION_OK"
        assert out["result"]["code"] == "WINDOWS_TOOLS_LAUNCH_OK"
        assert out["result"]["result"]["code"] == "LAUNCH_OK"


def test_control_panel_launch_item_action():
    out = invoke_item_action(
        "Command Prompt",
        "launch_item",
        {},
        corr="corr_cp_launch_item_001",
    )
    assert out["ok"] is True
    assert out["code"] == "CONTROL_PANEL_ACTION_OK"
    assert out["result"]["code"] == "WINDOWS_TOOLS_LAUNCH_OK"
    assert out["result"]["result"]["code"] == "LAUNCH_OK"


def test_control_panel_one_click_connect_action():
    app_id = "cp_click_demo"
    inbox_dir = MODULES_INBOX_PATH / app_id
    inbox_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = inbox_dir / "module.json"
    manifest = {
        "app_id": app_id,
        "name": "Control Panel Click Demo",
        "version": "0.1.0",
        "install_mode": "copy_in_place",
        "activation_mode": "one_click_add_to_os",
        "runtime_mode": "capsule"
    }
    manifest["provenance"] = build_module_provenance_envelope(
        str(manifest_path),
        manifest,
        source_commit_sha="0101010101010101010101010101010101010101",
        build_pipeline_id="axion-test-modules",
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    out = invoke_item_action("Program Modules", "one_click_connect", {"app_id": app_id}, corr="corr_cp_click_001")
    assert out["ok"] is True
    assert out["code"] == "CONTROL_PANEL_ACTION_OK"
    assert out["result"]["code"] == "PROGRAM_MODULE_CONNECTED"
    assert (MODULES_CATALOG_PATH / app_id / "module.json").exists()
    assert (MODULES_RECEIPTS_PATH / f"{app_id}.json").exists()

    cleanup = remove_program_module(app_id)
    assert cleanup["ok"]


def test_control_panel_run_installer_action():
    provenance = build_installer_provenance_envelope(
        "cp_setup_legacy.deb",
        family="linux",
        profile="linux_current",
        source_commit_sha="0202020202020202020202020202020202020202",
        build_pipeline_id="axion-test-installers",
    )
    out = invoke_item_action(
        "Programs and Features",
        "run_installer",
        {
            "installer_path": "cp_setup_legacy.deb",
            "family": "linux",
            "profile": "linux_current",
            "execute": True,
            "provenance": provenance,
        },
        corr="corr_cp_installer_001",
    )
    assert out["ok"] is True
    assert out["code"] == "CONTROL_PANEL_ACTION_OK"
    assert out["result"]["code"] == "LAUNCH_INSTALLER_EXECUTED"


def test_control_panel_firewall_quarantine_actions():
    qdir = Path(MODULES_INBOX_PATH.parents[2] / "quarantine" / "network_packets" / "external_installer" / "cp-test")
    qdir.mkdir(parents=True, exist_ok=True)
    qpath = qdir / "20260417T000000000001Z_test.json"
    qpath.write_text(
        json.dumps(
            {
                "reason": "FIREWALL_REMOTE_HOST_MISMATCH",
                "session_id": "cp-test",
                "app_id": "external_installer",
                "packet": {
                    "direction": "egress",
                    "protocol": "https",
                    "remote_host": "cp-quarantine.example.net",
                    "remote_port": 443,
                    "flow_profile": "installer_update",
                },
                "quarantined_utc": "2026-04-17T00:00:00Z",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    listed = invoke_item_action(
        "Windows Defender Firewall",
        "review_firewall_quarantine",
        {"app_id": "external_installer", "limit": 20},
        corr="corr_cp_fwq_list_001",
    )
    assert listed["ok"] is True
    assert listed["result"]["code"] == "FIREWALL_QUARANTINE_LIST_OK"
    assert any(str(x.get("path")) == str(qpath) for x in (listed["result"].get("items") or []))

    allowed = invoke_item_action(
        "Windows Defender Firewall",
        "allow_firewall_quarantine",
        {"path": str(qpath), "note": "allow from control panel test"},
        corr="corr_cp_fwq_allow_001",
    )
    assert allowed["ok"] is True
    assert allowed["result"]["code"] == "FIREWALL_QUARANTINE_ADJUDICATED"

    replayed = invoke_item_action(
        "Windows Defender Firewall",
        "replay_firewall_quarantine",
        {"path": str(qpath)},
        corr="corr_cp_fwq_replay_001",
    )
    assert replayed["ok"] is True
    assert replayed["result"]["code"] == "FIREWALL_QUARANTINE_REPLAY_OK"


def test_control_panel_smart_driver_fabric_actions():
    status = invoke_item_action(
        "Smart Driver Fabric",
        "smart_driver_fabric_status",
        {},
        corr="corr_cp_sdf_status_001",
    )
    assert status["ok"] is True
    assert status["result"]["code"] in ("SMART_DRIVER_FABRIC_READY", "SMART_DRIVER_FABRIC_REUSED")

    refresh = invoke_item_action(
        "Smart Driver Fabric",
        "smart_driver_fabric_refresh",
        {"force_rebuild": False, "build_handoff": True},
        corr="corr_cp_sdf_refresh_001",
    )
    assert refresh["ok"] is True
    assert refresh["result"]["code"] == "SMART_DRIVER_FABRIC_REFRESH_OK"
    assert (refresh["result"].get("kernel_handoff") or {}).get("code") == "SMART_DRIVER_KERNEL_HANDOFF_READY"


def test_control_panel_smart_driver_builder_actions():
    snap = invoke_item_action(
        "Smart Driver Builder",
        "smart_driver_builder_snapshot",
        {},
        corr="corr_cp_sdb_snapshot_001",
    )
    assert snap["ok"] is True
    assert snap["result"]["code"] == "SMART_DRIVER_BUILDER_SNAPSHOT_OK"
    assert snap["result"]["title"] == "Smart Driver Builder"

    submitted = invoke_item_action(
        "Smart Driver Builder",
        "smart_driver_builder_submit_issues",
        {
            "issues": [
                {"summary": "Bluetooth reconnect lag", "frequency": "always"},
                "USB HID wake resume delay",
            ],
            "reporter": "control_panel_test",
            "device_context": {"board_family": "q35_ovmf_ref"},
        },
        corr="corr_cp_sdb_submit_001",
    )
    assert submitted["ok"] is True
    assert submitted["result"]["code"] == "SMART_DRIVER_BUILDER_ISSUES_CAPTURED"
    report_id = submitted["result"]["report"]["report_id"]

    rebuilt = invoke_item_action(
        "Smart Driver Builder",
        "smart_driver_builder_rebuild",
        {"report_id": report_id, "force_rebuild": True, "build_handoff": True},
        corr="corr_cp_sdb_rebuild_001",
    )
    assert rebuilt["ok"] is True
    assert rebuilt["result"]["code"] == "SMART_DRIVER_BUILDER_REBUILD_OK"
    assert (rebuilt["result"].get("kernel_handoff") or {}).get("code") == "SMART_DRIVER_KERNEL_HANDOFF_READY"


def test_control_panel_firmware_bios_settings_actions():
    staged = invoke_item_action(
        "Firmware and BIOS Settings",
        "stage_bios_settings",
        {
            "settings": {
                "virtualization": True,
                "iommu": True,
                "secure_boot_mode": "standard",
            },
            "actor": "control_panel_test",
        },
        corr="corr_cp_bios_stage_001",
    )
    assert staged["ok"] is True
    assert staged["result"]["code"] == "BIOS_SETTINGS_STAGED_PENDING_RESTART"

    pending = invoke_item_action(
        "Firmware and BIOS Settings",
        "get_pending_bios_settings",
        {},
        corr="corr_cp_bios_pending_001",
    )
    assert pending["ok"] is True
    assert pending["result"]["code"] in ("BIOS_SETTINGS_PENDING_FOUND", "BIOS_SETTINGS_NONE_PENDING")


def test_control_panel_shadow_copy_actions():
    axion_root = MODULES_INBOX_PATH.parents[3]
    target = Path(axion_root / "data" / "profiles" / "p1" / "Workspace" / "cp_shadow_copy_test")
    target.mkdir(parents=True, exist_ok=True)
    payload_file = target / "marker.txt"
    payload_file.write_text("before", encoding="utf-8")
    rel_target = str(target.relative_to(axion_root)).replace("\\", "/")
    scope_id = "cp_shadow_copy_scope"

    created = invoke_item_action(
        "Backup and Restore (Windows 7)",
        "create_shadow_copy",
        {
            "scope_id": scope_id,
            "target_paths": [rel_target],
            "reason": "cp_test",
        },
        corr="corr_cp_shadow_copy_create_001",
    )
    assert created["ok"] is True
    snapshot_id = (created.get("result") or {}).get("snapshot_id")
    assert snapshot_id

    payload_file.write_text("after", encoding="utf-8")
    rolled = invoke_item_action(
        "Backup and Restore (Windows 7)",
        "rollback_shadow_copy",
        {
            "scope_id": scope_id,
            "snapshot_id": snapshot_id,
        },
        corr="corr_cp_shadow_copy_rollback_001",
    )
    assert rolled["ok"] is True
    assert payload_file.read_text(encoding="utf-8") == "before"

    listed = invoke_item_action(
        "Backup and Restore (Windows 7)",
        "list_shadow_copies",
        {"scope_id": scope_id},
        corr="corr_cp_shadow_copy_list_001",
    )
    assert listed["ok"] is True
    assert (listed.get("result") or {}).get("count", 0) >= 1


def test_control_panel_runtime_operation_action():
    opened = invoke_item_action(
        "Slides",
        "runtime_operation",
        {"operation": "open_document", "args": {"doc_name": "cp_runtime_slides"}},
        corr="corr_cp_runtime_open_001",
    )
    assert opened["ok"] is True
    assert opened["result"]["code"] == "WINDOWS_TOOLS_ACTION_OK"

    exported = invoke_item_action(
        "Slides",
        "runtime_operation",
        {"operation": "export_document", "args": {"doc_name": "cp_runtime_slides", "export_format": "pdf"}},
        corr="corr_cp_runtime_export_001",
    )
    assert exported["ok"] is True
    assert exported["result"]["code"] == "WINDOWS_TOOLS_ACTION_OK"
