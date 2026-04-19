import json
import subprocess
import sys
from pathlib import Path


def test_emit_completion_assessment_runs():
    root = Path(__file__).resolve().parents[2]
    script = root / "tools" / "qa" / "emit_completion_assessment.py"
    out_json = root / "out" / "qa" / "os_completion_assessment_latest.json"
    out_md = root / "out" / "qa" / "os_completion_assessment_latest.md"

    proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert out_json.exists()
    assert out_md.exists()
    obj = json.loads(out_json.read_text(encoding="utf-8-sig"))
    assert isinstance(obj.get("completion_score_pct"), (int, float))
    assert isinstance(obj.get("recommended_batches", []), list)
    gaps = obj.get("remaining_gaps", [])
    if not gaps:
        assert len(obj.get("recommended_batches", [])) == 0
    else:
        assert len(obj.get("recommended_batches", [])) >= 1
