from pathlib import Path

from driver_artifact_compiler import compile_driver_bundle_to_signed_artifact


def test_compile_driver_bundle_to_signed_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_KMS_RELEASE_SIGNING_KEY_01", "test-driver-artifact-key")
    bundle_dir = tmp_path / "driver_bundle"
    (bundle_dir / "src").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "tests").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "docs").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "bundle_manifest.json").write_text(
        (
            "{\n"
            '  "driver_id": "drv_sdf_q35_security_trust_v1",\n'
            '  "driver_class": "security_trust",\n'
            '  "target_family": "q35",\n'
            '  "version": "0.1.0"\n'
            "}\n"
        ),
        encoding="utf-8",
    )
    (bundle_dir / "src" / "driver_entry.c").write_text(
        "int axdrv_drv_sdf_q35_security_trust_v1_entry(void){return 0;}\n",
        encoding="utf-8",
    )

    out = compile_driver_bundle_to_signed_artifact(
        bundle_dir=bundle_dir,
        artifact_root=tmp_path / "artifacts",
        build_pipeline_id="axion-test-driver-artifact",
        source_commit_sha="abababababababababababababababababababab",
    )
    assert out["ok"] is True, out
    assert out["code"] == "DRIVER_ARTIFACT_COMPILED_SIGNED"
    assert Path(out["artifact_path"]).exists()
    assert Path(out["provenance_path"]).exists()
    assert Path(out["receipt_path"]).exists()
