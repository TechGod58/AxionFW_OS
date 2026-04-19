import csv
import io
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "data" / "apps" / "task_manager"
ROOT.mkdir(parents=True, exist_ok=True)
ACTIONS_PATH = ROOT / "actions.ndjson"

_PRIORITIES = {"idle", "below_normal", "normal", "above_normal", "high", "realtime"}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _append_action(entry: dict):
    with ACTIONS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def _parse_mem_to_kb(text: str) -> int:
    raw = str(text or "").replace(",", "").strip().lower()
    if raw.endswith("k"):
        raw = raw[:-1]
    try:
        return int(raw)
    except Exception:
        return 0


def _collect_tasklist(limit: int = 96):
    proc = subprocess.run(
        ["tasklist", "/fo", "csv", "/nh"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        return []
    reader = csv.reader(io.StringIO(proc.stdout))
    out = []
    for row in reader:
        if len(row) < 5:
            continue
        image_name, pid, session_name, _, mem = row[:5]
        try:
            pid_int = int(str(pid).strip())
        except Exception:
            continue
        out.append(
            {
                "pid": pid_int,
                "name": str(image_name).strip(),
                "session_name": str(session_name).strip(),
                "memory_kb": _parse_mem_to_kb(mem),
                "state": "running",
                "source": "tasklist",
            }
        )
        if len(out) >= max(1, int(limit)):
            break
    return out


def collect_tasks(limit: int = 96):
    tasks = _collect_tasklist(limit=limit)
    if tasks:
        return tasks
    return [
        {
            "pid": int(os.getpid()),
            "name": "python",
            "session_name": "fallback",
            "memory_kb": 0,
            "state": "running",
            "source": "fallback",
        }
    ]


def snapshot(limit: int = 96):
    tasks = collect_tasks(limit=limit)
    status = "PASS" if tasks else "FAIL"
    failures = [] if tasks else [{"code": "TASK_MANAGER_EMPTY"}]
    return {
        "ok": True,
        "code": "TASK_MANAGER_SNAPSHOT_OK",
        "status": status,
        "tasks": tasks,
        "failures": failures,
        "summary": {
            "running": len(tasks),
            "timestamp_utc": _now_iso(),
            "source": str((tasks[0] if tasks else {}).get("source", "none")),
        },
        "actions": ["refresh", "terminate_task", "set_priority"],
    }


def terminate_task(pid: int, *, allow_live: bool = False):
    pid_int = int(pid)
    if pid_int <= 0:
        return {"ok": False, "code": "TASK_MANAGER_PID_INVALID", "pid": pid_int}
    if pid_int == int(os.getpid()):
        return {"ok": False, "code": "TASK_MANAGER_TERMINATE_SELF_DENIED", "pid": pid_int}
    if not bool(allow_live):
        out = {"ok": True, "code": "TASK_MANAGER_TERMINATE_SIMULATED", "pid": pid_int}
        _append_action({"ts": _now_iso(), "action": "terminate_task", **out})
        return out

    proc = subprocess.run(
        ["taskkill", "/PID", str(pid_int), "/T", "/F"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out = {
        "ok": proc.returncode == 0,
        "code": "TASK_MANAGER_TERMINATE_OK" if proc.returncode == 0 else "TASK_MANAGER_TERMINATE_FAILED",
        "pid": pid_int,
        "stderr": (proc.stderr or "").strip()[:240],
    }
    _append_action({"ts": _now_iso(), "action": "terminate_task", **out})
    return out


def set_priority(pid: int, priority: str):
    pid_int = int(pid)
    normalized = str(priority or "").strip().lower()
    if pid_int <= 0:
        return {"ok": False, "code": "TASK_MANAGER_PID_INVALID", "pid": pid_int}
    if normalized not in _PRIORITIES:
        return {
            "ok": False,
            "code": "TASK_MANAGER_PRIORITY_INVALID",
            "pid": pid_int,
            "allowed": sorted(_PRIORITIES),
        }
    out = {
        "ok": True,
        "code": "TASK_MANAGER_PRIORITY_SET_SIMULATED",
        "pid": pid_int,
        "priority": normalized,
    }
    _append_action({"ts": _now_iso(), "action": "set_priority", **out})
    return out


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
