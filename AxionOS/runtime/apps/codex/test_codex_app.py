from codex_app import snapshot, start_session


def test_codex_snapshot_and_session_start():
    before = snapshot()
    out = start_session("health check", profile="test")
    after = snapshot()
    assert out["ok"] is True
    assert out["code"] == "CODEX_SESSION_STARTED"
    assert after["app_id"] == "codex"
    assert after["session_count"] >= before["session_count"]
