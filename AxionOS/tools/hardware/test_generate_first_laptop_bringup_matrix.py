import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "hardware" / "generate_first_laptop_bringup_matrix.py"
INPUT = ROOT / "out" / "hardware_inventory" / "windows_hardware_inventory.json"
JSON_OUT = ROOT / "out" / "hardware_inventory" / "test_first_laptop_family_bringup_matrix.json"
MD_OUT = ROOT / "out" / "hardware_inventory" / "test_first_laptop_family_bringup_matrix.md"


def test_generate_first_laptop_bringup_matrix_smoke():
    subprocess.run([
        "python",
        str(SCRIPT),
        str(INPUT),
        str(INPUT),
        "--json-out",
        str(JSON_OUT),
        "--md-out",
        str(MD_OUT),
    ], check=True)
    payload = json.loads(JSON_OUT.read_text(encoding="utf-8-sig"))
    assert payload["matrix_id"] == "first_laptop_family_bringup_matrix_v1"
    assert payload["bringup_workstreams"]
    assert MD_OUT.exists()
