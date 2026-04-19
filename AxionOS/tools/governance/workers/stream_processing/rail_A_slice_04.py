import sys
from pathlib import Path

_TOOLS_DIR = None
for _parent in Path(__file__).resolve().parents:
    if (_parent / "tools" / "common" / "pathing.py").exists():
        _TOOLS_DIR = _parent / "tools"
        break
if _TOOLS_DIR and str(_TOOLS_DIR) not in sys.path:
    sys.path.append(str(_TOOLS_DIR))

from common.pathing import axion_path


def axion_path_str(*parts):
    return str(axion_path(*parts))
import json, os, subprocess, sys, threading
from datetime import datetime, timezone

WORKER_ID = "rail_A_slice_04"
STEP_NAME = "slice_message_ordering_consistency"
OUT_DIR = axion_path_str('out', 'governance', 'rails', 'workers')

# Fill these with the exact commands that exist in AxionOS.
# Example: [sys.executable, axion_path_str('tools', 'runtime', '<flow>.py')]
COMMANDS = [
    [sys.executable, axion_path_str('tools', 'runtime', 'message_ordering_consistency_integrity_flow.py')]
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def heartbeat(stop_evt: threading.Event, interval_s: int = 35):
    while not stop_evt.wait(interval_s):
        print(f"[heartbeat] {WORKER_ID} {STEP_NAME} t={utc_now()}", flush=True)


def run_cmd(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "cmd": cmd,
        "returncode": p.returncode,
        "stdout": p.stdout[-4000:],
        "stderr": p.stderr[-4000:],
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    res_path = os.path.join(OUT_DIR, f"{WORKER_ID}_result.json")
    print(f"[PHASE_START] {WORKER_ID} {STEP_NAME} t={utc_now()}", flush=True)

    stop_evt = threading.Event()
    t = threading.Thread(target=heartbeat, args=(stop_evt,), daemon=True)
    t.start()

    result = {
        "worker_id": WORKER_ID,
        "step_name": STEP_NAME,
        "started_utc": utc_now(),
        "status": "FAIL",
        "commands": [],
        "notes": [],
    }

    exit_code = 0
    try:
        if not COMMANDS:
            result["notes"].append("COMMANDS list is empty; wire to the real AxionOS command(s).")
            exit_code = 2
            return exit_code

        for cmd in COMMANDS:
            r = run_cmd(cmd)
            result["commands"].append(r)
            if r["returncode"] != 0:
                exit_code = r["returncode"]
                return exit_code

        result["status"] = "PASS"
        return 0
    finally:
        result["ended_utc"] = utc_now()
        stop_evt.set()
        with open(res_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"[PHASE_DONE] {WORKER_ID} {STEP_NAME} status={result['status']} out={res_path}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())



