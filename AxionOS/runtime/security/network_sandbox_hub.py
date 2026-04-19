from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AXION_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = AXION_ROOT / "config" / "NETWORK_SANDBOX_HUB_POLICY_V1.json"
STATE_PATH = AXION_ROOT / "config" / "NETWORK_SANDBOX_HUB_STATE_V1.json"
AUDIT_PATH = AXION_ROOT / "data" / "audit" / "network_sandbox_hub.ndjson"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _audit(event: dict[str, Any]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = dict(event)
    row.setdefault("ts", _now_iso())
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _default_policy() -> dict[str, Any]:
    return {
        "version": 1,
        "policyId": "AXION_NETWORK_SANDBOX_HUB_POLICY_V1",
        "enabled": True,
        "fail_closed": True,
        "ingress_sandbox": {
            "session_id": "internet_ingress_hub",
            "default_ingress_adapter": "wired",
            "adapters": {
                "wired": {"enabled": True, "sandboxed": True},
                "wifi": {"enabled": True, "sandboxed": True},
                "bluetooth": {"enabled": True, "sandboxed": True},
                "vpn": {"enabled": True, "sandboxed": True},
                "rdp_admin": {"enabled": True, "sandboxed": True},
                "rdp_user": {"enabled": True, "sandboxed": True},
            },
        },
        "sharing_defaults": {
            "require_share_mapping": True,
            "allow_upload": False,
            "allow_download": True,
            "allowed_adapters": ["wired", "wifi", "bluetooth", "vpn"],
            "deny_if_quarantined": True,
        },
        "quarantine": {
            "auto_cutoff": True,
            "infected_signal_fields": ["sandbox_infection_signal", "infected_sandbox", "malware_detected"],
        },
    }


def _default_state() -> dict[str, Any]:
    return {
        "version": 1,
        "policyId": "AXION_NETWORK_SANDBOX_HUB_STATE_V1",
        "hub": {"session_id": "internet_ingress_hub", "active": True, "created_utc": None, "last_seen_utc": None},
        "shares": {},
        "quarantine_total": 0,
        "last_updated_utc": None,
    }


def _normalize_adapter(value: str | None, policy: dict[str, Any]) -> str:
    text = str(value or "").strip().lower()
    if text:
        return text
    return str(((policy.get("ingress_sandbox") or {}).get("default_ingress_adapter")) or "wired").strip().lower()


def load_policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        return _default_policy()
    try:
        obj = _load_json(POLICY_PATH)
    except Exception:
        return _default_policy()
    if not isinstance(obj, dict):
        return _default_policy()
    return obj


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        state = _default_state()
        _save_json(STATE_PATH, state)
        return state
    try:
        obj = _load_json(STATE_PATH)
    except Exception:
        state = _default_state()
        _save_json(STATE_PATH, state)
        return state
    if not isinstance(obj, dict):
        state = _default_state()
        _save_json(STATE_PATH, state)
        return state
    if not isinstance(obj.get("shares"), dict):
        obj["shares"] = {}
    if not isinstance(obj.get("hub"), dict):
        obj["hub"] = {}
    obj.setdefault("version", 1)
    obj.setdefault("policyId", "AXION_NETWORK_SANDBOX_HUB_STATE_V1")
    obj.setdefault("quarantine_total", 0)
    obj.setdefault("last_updated_utc", None)
    return obj


def save_state(state: dict[str, Any]) -> None:
    _save_json(STATE_PATH, state)


def ensure_ingress_hub(corr: str | None = None) -> dict[str, Any]:
    policy = load_policy()
    if not bool(policy.get("enabled", True)):
        return {"ok": True, "code": "NETWORK_SANDBOX_HUB_DISABLED", "hub_session_id": None}

    state = load_state()
    hub_cfg = dict(policy.get("ingress_sandbox") or {})
    sid = str(hub_cfg.get("session_id") or "internet_ingress_hub")
    hub = state.setdefault("hub", {})
    hub.setdefault("session_id", sid)
    if not hub.get("created_utc"):
        hub["created_utc"] = _now_iso()
    hub["active"] = True
    hub["last_seen_utc"] = _now_iso()
    state["last_updated_utc"] = _now_iso()
    save_state(state)
    _audit({"event": "network.hub.ensure", "ok": True, "hub_session_id": sid, "corr": corr})
    return {"ok": True, "code": "NETWORK_SANDBOX_HUB_READY", "hub_session_id": sid}


def _share_key(sandbox_id: str) -> str:
    text = str(sandbox_id or "").strip()
    return text if text else "app:unknown"


def share_internet_to_sandbox(
    *,
    app_id: str,
    sandbox_id: str,
    corr: str | None = None,
    allowed_adapters: list[str] | None = None,
    allow_upload: bool | None = None,
    allow_download: bool | None = None,
) -> dict[str, Any]:
    policy = load_policy()
    if not bool(policy.get("enabled", True)):
        return {"ok": True, "code": "NETWORK_SANDBOX_HUB_DISABLED", "share": None}

    ensured = ensure_ingress_hub(corr=corr)
    if not bool(ensured.get("ok")):
        return {"ok": False, "code": "NETWORK_SANDBOX_HUB_UNAVAILABLE", "share": None}
    hub_session_id = str(ensured.get("hub_session_id") or "")
    defaults = dict(policy.get("sharing_defaults") or {})
    adapters_cfg = dict((policy.get("ingress_sandbox") or {}).get("adapters") or {})
    default_adapters = [str(x).strip().lower() for x in defaults.get("allowed_adapters", []) if str(x).strip()]
    use_adapters = [str(x).strip().lower() for x in (allowed_adapters or default_adapters) if str(x).strip()]
    if not use_adapters:
        use_adapters = ["wired"]
    use_adapters = [x for x in use_adapters if isinstance(adapters_cfg.get(x), dict)]
    if not use_adapters:
        use_adapters = ["wired"] if isinstance(adapters_cfg.get("wired"), dict) else []

    state = load_state()
    shares = state.setdefault("shares", {})
    key = _share_key(sandbox_id)
    now = _now_iso()
    share = shares.get(key) if isinstance(shares.get(key), dict) else {}
    share.update(
        {
            "sandbox_id": key,
            "app_id": str(app_id),
            "hub_session_id": hub_session_id,
            "allowed_adapters": use_adapters,
            "allow_upload": bool(defaults.get("allow_upload", False)) if allow_upload is None else bool(allow_upload),
            "allow_download": bool(defaults.get("allow_download", True)) if allow_download is None else bool(allow_download),
            "quarantined": bool(share.get("quarantined", False)),
            "quarantine_reason": share.get("quarantine_reason"),
            "created_utc": str(share.get("created_utc") or now),
            "last_seen_utc": now,
        }
    )
    shares[key] = share
    # Keep app-level fallback share for non-tagged packet paths.
    app_fallback_key = _share_key(f"app:{app_id}")
    if app_fallback_key not in shares:
        shares[app_fallback_key] = dict(share, sandbox_id=app_fallback_key)
    state["last_updated_utc"] = now
    save_state(state)
    _audit(
        {
            "event": "network.hub.share",
            "ok": True,
            "app_id": app_id,
            "sandbox_id": key,
            "hub_session_id": hub_session_id,
            "adapters": use_adapters,
            "corr": corr,
        }
    )
    return {"ok": True, "code": "NETWORK_SANDBOX_SHARE_READY", "share": share}


def _resolve_share_for_packet(app_id: str, packet: dict[str, Any], state: dict[str, Any]) -> dict[str, Any] | None:
    shares = state.get("shares") or {}
    if not isinstance(shares, dict):
        return None
    packet_sandbox = str(packet.get("network_sandbox_id") or "").strip()
    if packet_sandbox and isinstance(shares.get(packet_sandbox), dict):
        return dict(shares.get(packet_sandbox) or {})
    app_fallback = f"app:{app_id}"
    if isinstance(shares.get(app_fallback), dict):
        return dict(shares.get(app_fallback) or {})
    return None


def evaluate_packet_route(
    *,
    app_id: str,
    packet: dict[str, Any],
    corr: str | None = None,
) -> dict[str, Any]:
    policy = load_policy()
    if not bool(policy.get("enabled", True)):
        return {"ok": True, "code": "NETWORK_SANDBOX_HUB_DISABLED"}

    ensured = ensure_ingress_hub(corr=corr)
    if not bool(ensured.get("ok")):
        return {"ok": False, "code": "NETWORK_SANDBOX_HUB_UNAVAILABLE"}
    hub_session_id = str(ensured.get("hub_session_id") or "")
    state = load_state()
    share = _resolve_share_for_packet(str(app_id), dict(packet or {}), state)
    defaults = dict(policy.get("sharing_defaults") or {})
    if bool(defaults.get("require_share_mapping", True)) and not isinstance(share, dict):
        return {"ok": False, "code": "NETWORK_SANDBOX_SHARE_MISSING", "hub_session_id": hub_session_id}

    if not isinstance(share, dict):
        return {"ok": True, "code": "NETWORK_SANDBOX_SHARE_OPTIONAL_BYPASS", "hub_session_id": hub_session_id}

    if bool(defaults.get("deny_if_quarantined", True)) and bool(share.get("quarantined", False)):
        return {
            "ok": False,
            "code": "NETWORK_SANDBOX_QUARANTINED",
            "sandbox_id": share.get("sandbox_id"),
            "reason": share.get("quarantine_reason"),
        }

    packet_hub = str(packet.get("network_hub_session_id") or "").strip()
    if packet_hub and packet_hub != str(share.get("hub_session_id") or ""):
        return {"ok": False, "code": "NETWORK_SANDBOX_HUB_SESSION_MISMATCH", "sandbox_id": share.get("sandbox_id")}

    adapters_cfg = dict((policy.get("ingress_sandbox") or {}).get("adapters") or {})
    adapter = _normalize_adapter(str(packet.get("ingress_adapter") or ""), policy)
    adapter_cfg = dict(adapters_cfg.get(adapter) or {})
    if not adapter_cfg:
        return {"ok": False, "code": "NETWORK_SANDBOX_ADAPTER_UNKNOWN", "adapter": adapter}
    if not bool(adapter_cfg.get("enabled", True)):
        return {"ok": False, "code": "NETWORK_SANDBOX_ADAPTER_DISABLED", "adapter": adapter}
    if not bool(adapter_cfg.get("sandboxed", True)):
        return {"ok": False, "code": "NETWORK_SANDBOX_ADAPTER_NOT_SANDBOXED", "adapter": adapter}

    allowed_adapters = {str(x).strip().lower() for x in (share.get("allowed_adapters") or []) if str(x).strip()}
    if allowed_adapters and adapter not in allowed_adapters:
        return {"ok": False, "code": "NETWORK_SANDBOX_ADAPTER_NOT_ALLOWED", "adapter": adapter}

    share["last_seen_utc"] = _now_iso()
    shares = state.setdefault("shares", {})
    shares[_share_key(str(share.get("sandbox_id") or ""))] = share
    state["last_updated_utc"] = _now_iso()
    save_state(state)
    return {
        "ok": True,
        "code": "NETWORK_SANDBOX_ROUTE_OK",
        "sandbox_id": share.get("sandbox_id"),
        "hub_session_id": share.get("hub_session_id"),
        "adapter": adapter,
        "allow_upload": bool(share.get("allow_upload", False)),
        "allow_download": bool(share.get("allow_download", True)),
    }


def quarantine_sandbox(
    *,
    sandbox_id: str,
    reason: str,
    corr: str | None = None,
) -> dict[str, Any]:
    key = _share_key(sandbox_id)
    state = load_state()
    shares = state.setdefault("shares", {})
    share = shares.get(key) if isinstance(shares.get(key), dict) else None
    if not isinstance(share, dict):
        return {"ok": False, "code": "NETWORK_SANDBOX_NOT_FOUND", "sandbox_id": key}
    share["quarantined"] = True
    share["quarantine_reason"] = str(reason or "quarantine")
    share["allow_upload"] = False
    share["allow_download"] = False
    share["last_seen_utc"] = _now_iso()
    shares[key] = share
    state["quarantine_total"] = int(state.get("quarantine_total", 0)) + 1
    state["last_updated_utc"] = _now_iso()
    save_state(state)
    _audit({"event": "network.hub.quarantine", "sandbox_id": key, "reason": share["quarantine_reason"], "corr": corr})
    return {"ok": True, "code": "NETWORK_SANDBOX_QUARANTINED", "sandbox_id": key, "reason": share["quarantine_reason"]}


def set_ingress_adapter_state(
    *,
    adapter: str,
    enabled: bool | None = None,
    sandboxed: bool | None = None,
    corr: str | None = None,
) -> dict[str, Any]:
    policy = load_policy()
    ingress = policy.setdefault("ingress_sandbox", {})
    adapters = ingress.setdefault("adapters", {})
    key = str(adapter or "").strip().lower()
    if not key:
        return {"ok": False, "code": "NETWORK_SANDBOX_ADAPTER_INVALID"}
    cfg = dict(adapters.get(key) or {"enabled": True, "sandboxed": True})
    if enabled is not None:
        cfg["enabled"] = bool(enabled)
    if sandboxed is not None:
        cfg["sandboxed"] = bool(sandboxed)
    adapters[key] = cfg
    _save_json(POLICY_PATH, policy)
    _audit({"event": "network.hub.adapter.updated", "adapter": key, "enabled": cfg.get("enabled"), "sandboxed": cfg.get("sandboxed"), "corr": corr})
    return {"ok": True, "code": "NETWORK_SANDBOX_ADAPTER_UPDATED", "adapter": key, "config": cfg}


def hub_status() -> dict[str, Any]:
    policy = load_policy()
    state = load_state()
    return {
        "ok": True,
        "code": "NETWORK_SANDBOX_HUB_STATUS_OK",
        "enabled": bool(policy.get("enabled", True)),
        "fail_closed": bool(policy.get("fail_closed", True)),
        "hub": dict(state.get("hub") or {}),
        "share_count": len((state.get("shares") or {}).keys()),
        "quarantine_total": int(state.get("quarantine_total", 0)),
        "last_updated_utc": state.get("last_updated_utc"),
        "adapters": dict(((policy.get("ingress_sandbox") or {}).get("adapters") or {})),
    }
