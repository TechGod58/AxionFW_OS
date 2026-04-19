from smart_driver_builder_host import snapshot, submit_issue_report, rebuild_from_issue_report


def test_smart_driver_builder_snapshot():
    out = snapshot("corr_sdb_snapshot_001")
    assert out["ok"] is True
    assert out["code"] == "SMART_DRIVER_BUILDER_SNAPSHOT_OK"
    assert out["title"] == "Smart Driver Builder"
    assert "fabric_status" in out


def test_smart_driver_builder_submit_and_rebuild():
    captured = submit_issue_report(
        [
            {
                "summary": "Audio stutter on startup",
                "symptom": "Audio drops for first 3 seconds",
                "frequency": "always",
                "affected_hardware": ["pci:8086:0f0c"],
                "notes": "Only after cold boot",
            },
            "Bluetooth reconnect delay after wake",
        ],
        corr="corr_sdb_submit_001",
        reporter="test_suite",
        device_context={"board_family": "q35_ovmf_ref"},
    )
    assert captured["ok"] is True
    assert captured["code"] == "SMART_DRIVER_BUILDER_ISSUES_CAPTURED"
    report = captured["report"]
    assert report["issue_count"] == 2

    rebuilt = rebuild_from_issue_report(
        report_id=report["report_id"],
        corr="corr_sdb_rebuild_001",
        force_rebuild=True,
        build_handoff=True,
    )
    assert rebuilt["ok"] is True
    assert rebuilt["code"] == "SMART_DRIVER_BUILDER_REBUILD_OK"
    assert (rebuilt.get("status") or {}).get("code") in ("SMART_DRIVER_FABRIC_READY", "SMART_DRIVER_FABRIC_REUSED")
    assert (rebuilt.get("kernel_handoff") or {}).get("code") == "SMART_DRIVER_KERNEL_HANDOFF_READY"

