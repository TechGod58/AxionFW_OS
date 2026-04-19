from pathlib import Path
import subprocess
import json


def test_create_driver_bundle(tmp_path):
    script = Path(__file__).resolve().parent / "create_driver_bundle.py"
    driver_root = tmp_path / "driverkit"
    result = subprocess.run([
        "python",
        str(script),
        "--driver-id", "drv_sbx_audio_capture_broker",
        "--driver-class", "sandbox_mediation",
        "--target-family", "generic_x64_uefi",
        "--root", str(driver_root)
    ], capture_output=True, text=True)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    bundle_dir = Path(payload["bundle_dir"])
    assert (bundle_dir / "bundle_manifest.json").exists()
    manifest = json.loads((bundle_dir / "bundle_manifest.json").read_text(encoding="utf-8-sig"))
    assert manifest["driver_class"] == "sandbox_mediation"
