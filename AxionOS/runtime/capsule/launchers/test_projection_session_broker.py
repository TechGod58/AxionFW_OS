from datetime import datetime, timedelta, timezone
from pathlib import Path

from sandbox_projection import ensure_projection
from projection_session_broker import (
    close_session,
    load_session_registry,
    reap_expired_sessions,
    save_session_registry,
    start_or_reconnect_session,
)


def test_projection_session_start_and_reconnect():
    app_id = "session_broker_demo"
    projection = ensure_projection(
        app_id=app_id,
        family="linux",
        profile="linux_current",
        execution_model="sandbox_linux_compat",
        source="unit_test",
        installer_path="session_broker_demo.deb",
    )
    first = start_or_reconnect_session(app_id, projection, corr="corr_session_broker_001")
    assert first["ok"] is True
    if first["code"] == "PROJECTION_SESSION_RECONNECTED":
        close_session(first["session"]["session_id"], reason="reset_for_test")
        first = start_or_reconnect_session(app_id, projection, corr="corr_session_broker_001_reset")
        assert first["ok"] is True
    assert first["code"] == "PROJECTION_SESSION_STARTED"
    sid = first["session"]["session_id"]
    layer = first["session"]["runtime_layer"]
    assert layer["mode"] == "copy_on_write"

    second = start_or_reconnect_session(app_id, projection, corr="corr_session_broker_002")
    assert second["ok"] is True
    assert second["code"] == "PROJECTION_SESSION_RECONNECTED"
    assert second["session"]["session_id"] == sid

    closed = close_session(sid, reason="test_complete")
    assert closed["ok"] is True

    third = start_or_reconnect_session(app_id, projection, corr="corr_session_broker_003")
    assert third["ok"] is True
    assert third["session"]["session_id"] != sid


def test_projection_session_idle_timeout_reap_and_restart():
    app_id = "session_broker_expire"
    projection = ensure_projection(
        app_id=app_id,
        family="linux",
        profile="linux_current",
        execution_model="sandbox_linux_compat",
        source="unit_test",
        installer_path="session_broker_expire.deb",
    )
    started = start_or_reconnect_session(app_id, projection, corr="corr_session_expire_001")
    assert started["ok"] is True
    sid = started["session"]["session_id"]

    reg = load_session_registry()
    sess = reg["sessions"][sid]
    sess["idle_timeout_sec"] = 1
    sess["last_seen_utc"] = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    save_session_registry(reg)

    reap = reap_expired_sessions(corr="corr_session_expire_002")
    assert reap["ok"] is True
    assert sid in reap["expired_ids"]

    next_session = start_or_reconnect_session(app_id, projection, corr="corr_session_expire_003")
    assert next_session["ok"] is True
    assert next_session["session"]["session_id"] != sid


def test_close_session_purges_unsaved_overlay():
    app_id = "session_broker_purge"
    projection = ensure_projection(
        app_id=app_id,
        family="linux",
        profile="linux_current",
        execution_model="sandbox_linux_compat",
        source="unit_test",
        installer_path="session_broker_purge.deb",
    )
    started = start_or_reconnect_session(app_id, projection, corr="corr_session_purge_001")
    assert started["ok"] is True
    sid = started["session"]["session_id"]
    runtime_layer = dict(started["session"]["runtime_layer"])

    upper_file = Path(str(runtime_layer["upper"])) / "unsaved.tmp"
    work_file = Path(str(runtime_layer["work"])) / "work.tmp"
    upper_file.write_text("scratch", encoding="utf-8")
    work_file.write_text("scratch", encoding="utf-8")
    assert upper_file.exists() and work_file.exists()

    closed = close_session(sid, reason="test_purge")
    assert closed["ok"] is True
    assert closed["overlay_cleanup"]["ok"] is True
    assert upper_file.exists() is False
    assert work_file.exists() is False
