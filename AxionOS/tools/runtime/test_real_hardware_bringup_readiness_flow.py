import json
import subprocess
from pathlib import Path
from runtime_paths import axion_path_str

SCRIPT = Path(axion_path_str("tools", "runtime", "real_hardware_bringup_readiness_flow.py"))
SMOKE = Path(axion_path_str("out", "runtime", "real_hardware_bringup_readiness_smoke.json"))


def test_real_hardware_bringup_readiness_flow_passes():
    subprocess.run(["python", str(SCRIPT)], check=True)
    payload = json.loads(SMOKE.read_text(encoding="utf-8-sig"))
    assert payload["status"] == "PASS"
    assert payload["contract_id"] == "real_hardware_bringup_readiness"
