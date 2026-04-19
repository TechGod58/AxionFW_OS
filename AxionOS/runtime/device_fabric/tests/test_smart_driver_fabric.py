from pathlib import Path

from smart_driver_fabric import ensure_fabric_initialized


def _q35_inventory():
    return [
        {"bus": "pci", "vendor": "8086", "product": "29c0", "bsp": "bsp_q35_ovmf_ref_v1"},
        {"bus": "pci", "vendor": "8086", "product": "2918", "bsp": "bsp_q35_ovmf_ref_v1"},
        {"bus": "pci", "vendor": "1af4", "product": "1042", "bsp": "bsp_q35_ovmf_ref_v1"},
        {"bus": "sandbox", "profile": "persistent_profile_sandbox", "bsp": "bsp_q35_ovmf_ref_v1"},
    ]


def test_smart_driver_fabric_materializes_missing_required_classes(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_KMS_RELEASE_SIGNING_KEY_01", "test-smart-driver-key")
    state_path = tmp_path / "state" / "smart_driver_fabric_state.json"
    plan_path = tmp_path / "plan" / "smart_driver_fabric_plan.json"
    bundle_root = tmp_path / "bundles"
    artifact_root = tmp_path / "artifacts"
    artifact_registry_path = tmp_path / "state" / "smart_driver_fabric_artifact_registry.json"

    out = ensure_fabric_initialized(
        corr="corr_sdf_test_materialize_001",
        hardware_inventory=_q35_inventory(),
        force_rebuild=True,
        config_override={
            "state_path": str(state_path),
            "plan_path": str(plan_path),
            "bundle_root": str(bundle_root),
            "artifact_root": str(artifact_root),
            "artifact_registry_path": str(artifact_registry_path),
            "target_bsp_id": "bsp_q35_ovmf_ref_v1",
            "materialize_missing_required_classes": True,
            "compile_signed_loadable_artifacts": True,
        },
    )
    assert out["ok"] is True, out
    assert out["code"] == "SMART_DRIVER_FABRIC_READY", out
    assert plan_path.exists()
    assert state_path.exists()

    synthesized_classes = sorted({item["driver_class"] for item in out.get("synthesized_drivers", [])})
    assert "firmware_handoff" in synthesized_classes
    assert "security_trust" in synthesized_classes
    for item in out.get("synthesized_drivers", []):
        assert Path(item["bundle_manifest_path"]).exists()
    assert artifact_registry_path.exists()
    assert len(out.get("compiled_artifacts", [])) >= 1
    assert out.get("artifact_compile_failures", []) == []


def test_smart_driver_fabric_reuses_single_load_state(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_KMS_RELEASE_SIGNING_KEY_01", "test-smart-driver-key")
    state_path = tmp_path / "state" / "smart_driver_fabric_state.json"
    plan_path = tmp_path / "plan" / "smart_driver_fabric_plan.json"
    bundle_root = tmp_path / "bundles"
    artifact_root = tmp_path / "artifacts"
    artifact_registry_path = tmp_path / "state" / "smart_driver_fabric_artifact_registry.json"
    cfg = {
        "state_path": str(state_path),
        "plan_path": str(plan_path),
        "bundle_root": str(bundle_root),
        "artifact_root": str(artifact_root),
        "artifact_registry_path": str(artifact_registry_path),
        "target_bsp_id": "bsp_q35_ovmf_ref_v1",
        "materialize_missing_required_classes": True,
        "compile_signed_loadable_artifacts": True,
        "one_time_bootstrap": True,
    }

    first = ensure_fabric_initialized(
        corr="corr_sdf_test_reuse_001",
        hardware_inventory=_q35_inventory(),
        force_rebuild=True,
        config_override=cfg,
    )
    assert first["ok"] is True, first
    assert first["code"] == "SMART_DRIVER_FABRIC_READY", first

    second = ensure_fabric_initialized(
        corr="corr_sdf_test_reuse_002",
        hardware_inventory=_q35_inventory(),
        force_rebuild=False,
        config_override=cfg,
    )
    assert second["ok"] is True, second
    assert second["code"] == "SMART_DRIVER_FABRIC_REUSED", second
    assert first["load_once_token"] == second["load_once_token"]
    assert second.get("artifact_compile_failures", []) == []
