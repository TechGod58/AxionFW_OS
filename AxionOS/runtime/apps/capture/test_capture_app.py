import json
from pathlib import Path

from capture_app import capture_fullscreen, capture_window, list_captures


def test_capture_flow():
    full = capture_fullscreen(corr="corr_capture_test_full")
    win = capture_window("w1", corr="corr_capture_test_window")
    assert full["ok"]
    assert win["ok"]

    full_payload = json.loads(Path(full["file"]).read_text(encoding="utf-8-sig"))
    win_payload = json.loads(Path(win["file"]).read_text(encoding="utf-8-sig"))
    assert full_payload["schema"] == "axion.capture.v1"
    assert win_payload["schema"] == "axion.capture.v1"
    assert isinstance(full_payload.get("fingerprint_sha256"), str) and len(full_payload["fingerprint_sha256"]) == 64
    assert isinstance(win_payload.get("fingerprint_sha256"), str) and len(win_payload["fingerprint_sha256"]) == 64

    out = list_captures()
    assert out["ok"] and out["count"] >= 2
