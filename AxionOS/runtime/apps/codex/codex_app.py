import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "data" / "apps" / "codex"
ROOT.mkdir(parents=True, exist_ok=True)
SESSIONS_PATH = ROOT / "sessions.ndjson"
STATE_PATH = ROOT / "state.json"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _append_session(entry: dict):
    with SESSIONS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def _read_sessions(limit: int = 16):
    if not SESSIONS_PATH.exists():
        return []
    lines = SESSIONS_PATH.read_text(encoding="utf-8").splitlines()
    recent = lines[-max(1, int(limit)) :]
    out = []
    for line in recent:
        try:
            payload = json.loads(line)
            if isinstance(payload, dict):
                out.append(payload)
        except Exception:
            continue
    return out


def start_session(prompt: str = "", profile: str = "assistant"):
    ts = datetime.now(timezone.utc)
    session_id = f"codex_{ts.strftime('%Y%m%dT%H%M%S%fZ')}"
    row = {
        "session_id": session_id,
        "ts": ts.isoformat(),
        "profile": str(profile or "assistant"),
        "prompt_preview": str(prompt or "").strip()[:140],
        "workspace": str(Path.cwd()),
        "user": str(os.getenv("USERNAME", "")),
    }
    _append_session(row)
    return {
        "ok": True,
        "code": "CODEX_SESSION_STARTED",
        "session": row,
    }


def snapshot():
    sessions = _read_sessions(limit=32)
    out = {
        "app": "Codex",
        "app_id": "codex",
        "ready": True,
        "workspace": str(Path.cwd()),
        "session_count": len(sessions),
        "recent_sessions": sessions[-5:],
        "updated_utc": _now_iso(),
    }
    STATE_PATH.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
