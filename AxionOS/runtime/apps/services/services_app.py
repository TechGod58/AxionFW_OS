import json
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


SERVICES_HOST_DIR = Path(axion_path_str("runtime", "shell_ui", "services_host"))
if str(SERVICES_HOST_DIR) not in sys.path:
    sys.path.append(str(SERVICES_HOST_DIR))

from services_host import (
    restart_service as host_restart_service,
    set_startup_type as host_set_startup_type,
    snapshot as host_snapshot,
    start_service as host_start_service,
    stop_service as host_stop_service,
)


def _normalize_services(raw: dict):
    rows = []
    services_map = (raw or {}).get("services", {}) if isinstance(raw, dict) else {}
    for service_id, meta in sorted(services_map.items()):
        if not isinstance(meta, dict):
            continue
        rows.append(
            {
                "service_id": str(service_id),
                "display_name": str(meta.get("display_name", service_id)),
                "state": str(meta.get("state", "stopped")),
                "startup_type": str(meta.get("startup_type", "manual")),
                "health": str(meta.get("health", "unknown")),
                "last_error": meta.get("last_error"),
                "protected": bool(meta.get("protected", False)),
            }
        )
    return rows


def snapshot(corr: str = "corr_services_app_snapshot_001"):
    base = host_snapshot(corr=corr)
    services = _normalize_services(base)
    status = "PASS" if services else "FAIL"
    failures = [] if services else [{"code": "SERVICES_EMPTY"}]
    return {
        "ok": True,
        "code": "SERVICES_APP_SNAPSHOT_OK",
        "status": status,
        "services": services,
        "failures": failures,
        "sections": list(base.get("sections", [])),
        "actions": list(base.get("actions", [])),
    }


def set_startup_type(service_id: str, startup_type: str, corr: str = "corr_services_app_startup_001"):
    out = host_set_startup_type(str(service_id), str(startup_type), corr=corr)
    return {"ok": bool(out.get("ok")), "code": str(out.get("code")), "service_id": str(service_id), "result": out}


def start_service(service_id: str, corr: str = "corr_services_app_start_001"):
    out = host_start_service(str(service_id), corr=corr)
    return {"ok": bool(out.get("ok")), "code": str(out.get("code")), "service_id": str(service_id), "result": out}


def stop_service(service_id: str, corr: str = "corr_services_app_stop_001"):
    out = host_stop_service(str(service_id), corr=corr)
    return {"ok": bool(out.get("ok")), "code": str(out.get("code")), "service_id": str(service_id), "result": out}


def restart_service(service_id: str, corr: str = "corr_services_app_restart_001"):
    out = host_restart_service(str(service_id), corr=corr)
    return {"ok": bool(out.get("ok")), "code": str(out.get("code")), "service_id": str(service_id), "result": out}


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
