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
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

BUS_LOG = Path(axion_path_str('data', 'audit', 'shell_event_bus.ndjson'))
_lock = RLock()
_subscribers = {}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _append_log(evt):
    BUS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with BUS_LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(evt) + '\n')


def subscribe(topic: str, handler_name: str):
    with _lock:
        _subscribers.setdefault(topic, set()).add(handler_name)
    return {"ok": True, "code": "BUS_SUBSCRIBED", "topic": topic, "handler": handler_name}


def unsubscribe(topic: str, handler_name: str):
    with _lock:
        if topic in _subscribers and handler_name in _subscribers[topic]:
            _subscribers[topic].remove(handler_name)
    return {"ok": True, "code": "BUS_UNSUBSCRIBED", "topic": topic, "handler": handler_name}


def publish(topic: str, payload: dict, corr: str = None, source: str = "shell"):
    with _lock:
        handlers = sorted(list(_subscribers.get(topic, set())))
    evt = {
        "ts": _now(),
        "topic": topic,
        "source": source,
        "corr": corr,
        "payload": payload,
        "handlers": handlers
    }
    _append_log(evt)
    return {"ok": True, "code": "BUS_PUBLISHED", "topic": topic, "handlers": handlers}


def snapshot_subscribers():
    with _lock:
        return {k: sorted(list(v)) for k, v in _subscribers.items()}


if __name__ == '__main__':
    print(json.dumps(snapshot_subscribers(), indent=2))

