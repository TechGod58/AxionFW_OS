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

CATALOG_PATH = Path(axion_path_str("config", "DEVICE_DRIVER_CATALOG_V1.json"))
STATE_PATH = Path(axion_path_str("data", "device_runtime", "rebind_state.json"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _device_key(device: dict) -> str:
    return f"{device.get('bus', '')}:{device.get('vendor', '')}:{device.get('product', '')}"


def _sanitized_device(device: dict) -> dict:
    return {"bus": device.get("bus"), "vendor": device.get("vendor"), "product": device.get("product")}


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        return obj if isinstance(obj, dict) else dict(default)
    except Exception:
        return dict(default)


def _load_catalog() -> dict:
    return _load_json(CATALOG_PATH, {"drivers": []})


def _load_state() -> dict:
    obj = _load_json(STATE_PATH, {"version": 1, "active_bindings": {}, "history": [], "last_updated_utc": None})
    obj.setdefault("version", 1)
    if not isinstance(obj.get("active_bindings"), dict):
        obj["active_bindings"] = {}
    if not isinstance(obj.get("history"), list):
        obj["history"] = []
    obj.setdefault("last_updated_utc", None)
    return obj


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _driver_in_catalog(driver_id: str) -> bool:
    cat = _load_catalog()
    for item in (cat.get("drivers") or []):
        if not isinstance(item, dict):
            continue
        if str(item.get("driver_id") or "") == str(driver_id):
            return True
    return False


def rebind_runtime(device: dict, driver_id: str):
    device = dict(device or {})
    clean = _sanitized_device(device)
    if not all(clean.get(k) for k in ("bus", "vendor", "product")):
        return {"ok": False, "code": "RUNTIME_REBIND_BAD_DEVICE", "device": clean, "driver_id": str(driver_id or "")}

    did = _device_key(clean)
    driver = str(driver_id or "").strip()
    if not driver:
        return {"ok": False, "code": "RUNTIME_REBIND_BAD_DRIVER_ID", "device": clean, "driver_id": driver}
    if not _driver_in_catalog(driver):
        return {"ok": False, "code": "RUNTIME_REBIND_DRIVER_NOT_APPROVED", "device": clean, "driver_id": driver}

    state = _load_state()
    existing = dict((state.get("active_bindings") or {}).get(did) or {})
    if str(existing.get("driver_id") or "") == driver:
        return {
            "ok": True,
            "code": "RUNTIME_REBIND_NOOP_ALREADY_BOUND",
            "device": clean,
            "driver_id": driver,
            "device_id": did,
        }

    entry = {
        "device_id": did,
        "device": clean,
        "driver_id": driver,
        "bound_utc": _now(),
    }
    state["active_bindings"][did] = dict(entry)
    state["history"].insert(0, dict(entry))
    state["history"] = state["history"][:256]
    state["last_updated_utc"] = _now()
    _save_state(state)

    return {
        "ok": True,
        "code": "RUNTIME_REBIND_OK",
        "device": clean,
        "driver_id": driver,
        "device_id": did,
    }
