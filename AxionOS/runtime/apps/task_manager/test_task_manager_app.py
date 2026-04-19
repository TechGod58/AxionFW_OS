import os

from task_manager_app import set_priority, snapshot, terminate_task


def test_task_manager_snapshot_has_tasks():
    out = snapshot()
    assert out["ok"] is True
    assert out["status"] in ("PASS", "FAIL")
    assert isinstance(out["tasks"], list)
    assert isinstance(out["failures"], list)
    assert out["tasks"]


def test_task_manager_rejects_self_terminate():
    out = terminate_task(os.getpid(), allow_live=False)
    assert out["ok"] is False
    assert out["code"] == "TASK_MANAGER_TERMINATE_SELF_DENIED"


def test_task_manager_priority_validation():
    bad = set_priority(1, "ultra")
    good = set_priority(1, "normal")
    assert bad["ok"] is False
    assert bad["code"] == "TASK_MANAGER_PRIORITY_INVALID"
    assert good["ok"] is True
    assert good["code"] == "TASK_MANAGER_PRIORITY_SET_SIMULATED"
