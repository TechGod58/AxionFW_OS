import json
from pathlib import Path

from services_app import set_startup_type, snapshot, start_service, stop_service

STATE_PATH = Path(__file__).resolve().parents[3] / "config" / "SERVICES_STATE_V1.json"


def _read_state():
    return json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))


def _write_state(state: dict):
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def test_services_snapshot_contract_shape():
    out = snapshot()
    assert out["ok"] is True
    assert out["status"] in ("PASS", "FAIL")
    assert isinstance(out["services"], list)
    assert any(row["service_id"] == "svc.shell" for row in out["services"])


def test_services_startup_and_start_stop_controls():
    baseline = _read_state()
    try:
        startup = set_startup_type("svc.updates", "manual")
        start = start_service("svc.updates")
        stop = stop_service("svc.shell")
        assert startup["ok"] is True
        assert start["ok"] is True
        assert stop["ok"] is False
        assert stop["code"] == "SERVICES_STOP_DENIED"
    finally:
        _write_state(baseline)
