from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
from pathlib import Path
import subprocess
import json


def test_axion_hal_platform_readiness_flow():
    script = Path(axion_path_str('tools', 'runtime', 'axion_hal_platform_readiness_flow.py'))
    result = subprocess.run(["python", str(script)], capture_output=True, text=True)
    assert result.returncode == 0
    smoke = Path(axion_path_str('out', 'runtime', 'axion_hal_platform_readiness_smoke.json'))
    obj = json.loads(smoke.read_text(encoding="utf-8-sig"))
    assert obj["status"] == "PASS"

