import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backup_restore_host import (
    create_shadow_copy,
    list_shadow_copies,
    load_policy,
    rollback_shadow_copy,
    run_shadow_copy_maintenance,
    axion_path_str,
)


def _scope_dir(scope_id: str) -> Path:
    return Path(axion_path_str("data", "shadow_copies", scope_id))


def _target_dir(scope_id: str) -> Path:
    return Path(axion_path_str("data", "profiles", "p1", "Workspace", f"shadow_copy_unit_{scope_id}"))


def test_shadow_copy_policy_defaults_weekly_keep_8():
    policy = load_policy()
    assert policy["schedule"]["frequency"] == "weekly"
    assert int(policy["schedule"]["interval_weeks"]) == 1
    assert int(policy["retention"]["max_copies"]) == 8


def test_shadow_copy_create_and_rollback_roundtrip():
    scope = "unit_shadow_roundtrip"
    shutil.rmtree(_scope_dir(scope), ignore_errors=True)
    target = _target_dir(scope)
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    file_path = target / "state.txt"
    file_path.write_text("v1", encoding="utf-8")

    created = create_shadow_copy(scope_id=scope, target_paths=[str(target.relative_to(Path(axion_path_str()))).replace("\\", "/")])
    assert created["ok"] is True
    snapshot_id = created["snapshot_id"]

    file_path.write_text("v2", encoding="utf-8")
    rolled = rollback_shadow_copy(snapshot_id=snapshot_id, scope_id=scope)
    assert rolled["ok"] is True
    assert file_path.read_text(encoding="utf-8") == "v1"


def test_shadow_copy_retention_caps_to_8():
    scope = "unit_shadow_retention"
    shutil.rmtree(_scope_dir(scope), ignore_errors=True)
    target = _target_dir(scope)
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    (target / "seed.txt").write_text("seed", encoding="utf-8")
    rel_target = str(target.relative_to(Path(axion_path_str()))).replace("\\", "/")

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for idx in range(10):
        when = (base + timedelta(days=idx)).isoformat()
        out = create_shadow_copy(
            scope_id=scope,
            target_paths=[rel_target],
            created_utc=when,
            reason=f"retention_{idx}",
        )
        assert out["ok"] is True

    listed = list_shadow_copies(scope_id=scope)
    assert listed["ok"] is True
    assert listed["count"] == 8


def test_shadow_copy_maintenance_skips_when_not_due():
    scope = "unit_shadow_maintenance"
    shutil.rmtree(_scope_dir(scope), ignore_errors=True)
    target = _target_dir(scope)
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    (target / "m.txt").write_text("m", encoding="utf-8")
    rel_target = str(target.relative_to(Path(axion_path_str()))).replace("\\", "/")

    first = run_shadow_copy_maintenance(
        scope_id=scope,
        force=True,
        now_utc="2026-01-01T00:00:00+00:00",
        target_paths=[rel_target],
    )
    assert first["ok"] is True
    skipped = run_shadow_copy_maintenance(
        scope_id=scope,
        force=False,
        now_utc="2026-01-03T00:00:00+00:00",
        target_paths=[rel_target],
    )
    assert skipped["ok"] is True
    assert skipped["code"] == "SHADOW_COPY_MAINTENANCE_SKIPPED_NOT_DUE"
