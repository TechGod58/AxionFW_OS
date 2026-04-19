from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from kernel_syscall_guard_bridge import evaluate_packet as kernel_guard_evaluate, add_allow_rule_for_packet
except Exception:
    kernel_guard_evaluate = None
    add_allow_rule_for_packet = None

try:
    from qm_ecc_bridge import evaluate_packet as qm_ecc_evaluate_packet
except Exception:
    qm_ecc_evaluate_packet = None

try:
    from profile_sandbox_guard import ensure_profile_sandbox_storage, evaluate_web_download_target
except Exception:
    ensure_profile_sandbox_storage = None
    evaluate_web_download_target = None
try:
    from network_sandbox_hub import (
        ensure_ingress_hub as ensure_network_ingress_hub,
        share_internet_to_sandbox as share_network_to_sandbox,
        evaluate_packet_route as evaluate_network_packet_route,
        quarantine_sandbox as quarantine_network_sandbox,
        load_policy as load_network_hub_policy,
    )
except Exception:
    ensure_network_ingress_hub = None
    share_network_to_sandbox = None
    evaluate_network_packet_route = None
    quarantine_network_sandbox = None
    load_network_hub_policy = None

AXION_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = AXION_ROOT / "config" / "FIREWALL_GUARD_POLICY_V1.json"
STATE_PATH = AXION_ROOT / "config" / "FIREWALL_GUARD_STATE_V1.json"
REVIEW_PATH = AXION_ROOT / "config" / "FIREWALL_QUARANTINE_REVIEW_V1.json"
PRIVSEC_PATH = AXION_ROOT / "config" / "PRIVACY_SECURITY_STATE_V1.json"
AUDIT_PATH = AXION_ROOT / "data" / "audit" / "firewall_guard.ndjson"
QUARANTINE_ROOT = AXION_ROOT / "data" / "quarantine" / "network_packets"


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


def load_policy() -> dict[str, Any]:
    return _load_json(POLICY_PATH)


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"version": 1, "policyId": "AXION_FIREWALL_GUARD_STATE_V1", "sessions": {}, "quarantine_total": 0, "last_updated_utc": None}
    try:
        return _load_json(STATE_PATH)
    except Exception:
        return {"version": 1, "policyId": "AXION_FIREWALL_GUARD_STATE_V1", "sessions": {}, "quarantine_total": 0, "last_updated_utc": None}


def save_state(state: dict[str, Any]) -> None:
    _save_json(STATE_PATH, state)


def _default_review_state() -> dict[str, Any]:
    return {
        "version": 1,
        "policyId": "AXION_FIREWALL_QUARANTINE_REVIEW_V1",
        "reviews": {},
        "last_updated_utc": None,
    }


def load_quarantine_review_state() -> dict[str, Any]:
    if not REVIEW_PATH.exists():
        return _default_review_state()
    try:
        obj = _load_json(REVIEW_PATH)
    except Exception:
        return _default_review_state()
    if not isinstance(obj, dict):
        return _default_review_state()
    obj.setdefault("version", 1)
    obj.setdefault("policyId", "AXION_FIREWALL_QUARANTINE_REVIEW_V1")
    if not isinstance(obj.get("reviews"), dict):
        obj["reviews"] = {}
    obj.setdefault("last_updated_utc", None)
    return obj


def save_quarantine_review_state(state: dict[str, Any]) -> None:
    _save_json(REVIEW_PATH, state)


def _effective_firewall_mode() -> str:
    if not PRIVSEC_PATH.exists():
        return "strict"
    try:
        obj = _load_json(PRIVSEC_PATH)
    except Exception:
        return "strict"
    mode = str(((obj.get("security") or {}).get("firewall_mode")) or "strict").lower()
    return "strict" if mode not in ("standard", "strict") else mode


def _resolve_profile(app_id: str, internet_hint: bool = False) -> dict[str, Any]:
    policy = load_policy()
    apps = policy.get("apps", {})
    default_profile = policy.get("default_internet_profile", {})
    app_raw = dict(apps.get(app_id, {}))
    raw = dict(app_raw)
    if raw.get("inherit"):
        inherited = dict(apps.get(str(raw.get("inherit")), {}))
        merged = dict(default_profile)
        merged.update(inherited)
        merged.update({k: v for k, v in raw.items() if k != "inherit"})
        raw = merged
    else:
        merged = dict(default_profile)
        merged.update(raw)
        raw = merged
    if app_id == "external_installer":
        raw["internet_required"] = True
    if internet_hint and ("internet_required" not in app_raw):
        raw["internet_required"] = True
    return raw


def _is_host_allowed(host: str, allowed: list[str]) -> bool:
    host = str(host or "").lower().strip()
    if not host:
        return False
    for rule in allowed:
        r = str(rule or "").lower().strip()
        if not r:
            continue
        if r.startswith("*."):
            suffix = r[1:]
            if host.endswith(suffix):
                return True
        elif host == r:
            return True
    return False


def _sanitize_token(value: str) -> str:
    out = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(value or "").strip().lower())
    out = out.strip("._-")
    return out or "packet"


def _normalize_effect(effect: str | None) -> str:
    val = str(effect or "").strip().lower()
    if val not in ("allow", "deny"):
        return "deny"
    return val


def _normalize_host_mode(host_rule: str, host_mode: str | None) -> str:
    raw = str(host_mode or "").strip().lower()
    if raw in ("exact", "suffix", "wildcard"):
        return raw
    if str(host_rule or "").strip().startswith("*."):
        return "wildcard"
    return "exact"


def _host_rule_match(host: str, host_rule: str, host_mode: str | None) -> bool:
    h = str(host or "").strip().lower()
    rule = str(host_rule or "").strip().lower()
    if not h or not rule:
        return False
    mode = _normalize_host_mode(rule, host_mode)
    if mode == "exact":
        return h == rule
    if mode == "suffix":
        return h.endswith(rule)
    if rule.startswith("*."):
        return h.endswith(rule[1:])
    return h == rule


def _to_int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _as_str_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _packet_transfer_type(packet: dict[str, Any]) -> str | None:
    raw = str(packet.get("transfer_type") or "").strip().lower()
    if raw in ("upload", "download", "control", "metadata"):
        return raw
    if bool(packet.get("is_upload", False)):
        return "upload"
    if bool(packet.get("is_download", False)):
        return "download"
    return None


def _packet_download_target_path(packet: dict[str, Any]) -> str | None:
    for key in ("save_path", "target_path", "destination_path", "download_path"):
        value = str(packet.get(key) or "").strip()
        if value:
            return value
    return None


def _packet_web_origin(packet: dict[str, Any]) -> bool:
    origin = str(packet.get("origin") or packet.get("channel") or "").strip().lower()
    if origin in ("web", "browser", "internet", "http", "https"):
        return True
    protocol = str(packet.get("protocol") or "").strip().lower()
    return protocol in ("http", "https")


def _web_save_guard_cfg(policy: dict[str, Any]) -> dict[str, Any]:
    raw = dict(policy.get("web_download_write_guard") or {})
    return {
        "enabled": bool(raw.get("enabled", True)),
        "profile_id_default": str(raw.get("profile_id_default") or "p1"),
        "require_target_path": bool(raw.get("require_target_path", True)),
        "require_profile_sandbox_target": bool(raw.get("require_profile_sandbox_target", True)),
        "deny_direct_c_root": bool(raw.get("deny_direct_c_root", True)),
        "allowed_profile_folders": _as_str_list(raw.get("allowed_profile_folders", [])),
        "allowed_vault_domains": _as_str_list(raw.get("allowed_vault_domains", [])),
    }


def _packet_rule_matches(rule: dict[str, Any], app_id: str, packet: dict[str, Any]) -> bool:
    app_selector = str(rule.get("app_id", "*") or "*").strip().lower()
    if app_selector not in ("*", app_id.lower()):
        return False

    direction = str(packet.get("direction", "egress") or "egress").lower()
    protocol = str(packet.get("protocol", "") or "").lower()
    host = str(packet.get("remote_host", "") or "").lower()
    flow = str(packet.get("flow_profile", "") or "").strip()
    port = _to_int_or_none(packet.get("remote_port"))

    req_direction = str(rule.get("direction", "") or "").strip().lower()
    if req_direction and direction != req_direction:
        return False

    req_protocol = str(rule.get("protocol", "") or "").strip().lower()
    if req_protocol and protocol != req_protocol:
        return False

    req_flow = str(rule.get("flow_profile", "") or "").strip()
    if req_flow and flow != req_flow:
        return False

    req_port = rule.get("remote_port")
    if isinstance(req_port, list):
        allowed = {_to_int_or_none(x) for x in req_port}
        if port not in allowed:
            return False
    else:
        req_one = _to_int_or_none(req_port)
        if req_one is not None and port != req_one:
            return False

    req_host = str(rule.get("remote_host", "") or "").strip().lower()
    if req_host and not _host_rule_match(host, req_host, rule.get("host_match")):
        return False
    return True


def _packet_rule_specificity(rule: dict[str, Any]) -> int:
    score = 0
    app_selector = str(rule.get("app_id", "*") or "*").strip().lower()
    if app_selector and app_selector != "*":
        score += 100
    if str(rule.get("direction", "") or "").strip():
        score += 8
    if str(rule.get("protocol", "") or "").strip():
        score += 8
    if str(rule.get("flow_profile", "") or "").strip():
        score += 6
    req_port = rule.get("remote_port")
    if isinstance(req_port, list) and req_port:
        score += 8
    elif _to_int_or_none(req_port) is not None:
        score += 8
    req_host = str(rule.get("remote_host", "") or "").strip()
    if req_host:
        host_mode = _normalize_host_mode(req_host, rule.get("host_match"))
        score += 20 if host_mode == "exact" else 12
    return score


def _rule_priority(rule: dict[str, Any]) -> int:
    try:
        return int(rule.get("priority", 0) or 0)
    except Exception:
        return 0


def _active_packet_rules(policy: dict[str, Any]) -> list[dict[str, Any]]:
    raw = policy.get("packet_rules", [])
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        if not bool(item.get("enabled", True)):
            continue
        out.append(dict(item))
    return out


def _select_packet_rule(policy: dict[str, Any], app_id: str, packet: dict[str, Any]) -> dict[str, Any] | None:
    candidates: list[tuple[int, int, int, dict[str, Any]]] = []
    for rule in _active_packet_rules(policy):
        if not _packet_rule_matches(rule, app_id, packet):
            continue
        specificity = _packet_rule_specificity(rule)
        priority = _rule_priority(rule)
        # Deny wins tie-breaks when specificity/priority are equal.
        deny_rank = 1 if _normalize_effect(str(rule.get("effect", "deny"))) == "deny" else 0
        candidates.append((specificity, priority, deny_rank, rule))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return candidates[0][3]


def _increment_quarantine_counter(count: int) -> None:
    if count <= 0:
        return
    if not PRIVSEC_PATH.exists():
        return
    try:
        state = _load_json(PRIVSEC_PATH)
    except Exception:
        return
    sec = state.setdefault("security", {})
    sec["quarantine_count"] = int(sec.get("quarantine_count", 0)) + int(count)
    _save_json(PRIVSEC_PATH, state)


def start_guard_session(app_id: str, corr: str | None = None, internet_hint: bool = False) -> dict[str, Any]:
    policy = load_policy()
    if not bool(policy.get("enabled", True)):
        return {"ok": True, "code": "FIREWALL_GUARD_DISABLED", "session": None}

    profile = _resolve_profile(app_id, internet_hint=internet_hint)
    mode = _effective_firewall_mode()
    required = bool(profile.get("internet_required", False))
    if not required:
        return {
            "ok": True,
            "code": "FIREWALL_GUARD_NOT_REQUIRED",
            "session": {"app_id": app_id, "internet_required": False, "mode": mode},
        }
    sid = f"{_sanitize_token(app_id)}-{secrets.token_hex(6)}"

    web_guard_cfg = _web_save_guard_cfg(policy)
    profile_storage = {"ok": True, "code": "PROFILE_SANDBOX_STORAGE_BYPASSED"}
    if callable(ensure_profile_sandbox_storage):
        profile_storage = ensure_profile_sandbox_storage(
            profile_id=str(web_guard_cfg.get("profile_id_default") or "p1"),
            allowed_folders=web_guard_cfg.get("allowed_profile_folders") or None,
            corr=corr,
        )
    if isinstance(profile_storage, dict) and not bool(profile_storage.get("ok", True)):
        return {
            "ok": False,
            "code": "FIREWALL_PROFILE_SANDBOX_UNAVAILABLE",
            "session": None,
            "profile_sandbox": profile_storage,
        }

    network_hub = {
        "ensure": {"ok": True, "code": "NETWORK_SANDBOX_HUB_BYPASSED"},
        "share": {"ok": True, "code": "NETWORK_SANDBOX_SHARE_BYPASSED"},
    }
    hub_fail_closed = True
    if callable(load_network_hub_policy):
        try:
            hub_fail_closed = bool((load_network_hub_policy() or {}).get("fail_closed", True))
        except Exception:
            hub_fail_closed = True
    if callable(ensure_network_ingress_hub):
        network_hub["ensure"] = ensure_network_ingress_hub(corr=corr)
    if callable(share_network_to_sandbox):
        network_hub["share"] = share_network_to_sandbox(
            app_id=str(app_id),
            sandbox_id=f"guard:{sid}",
            corr=corr,
        )
    if hub_fail_closed and (
        not bool((network_hub.get("ensure") or {}).get("ok", True))
        or not bool((network_hub.get("share") or {}).get("ok", True))
    ):
        return {
            "ok": False,
            "code": "FIREWALL_NETWORK_SANDBOX_HUB_UNAVAILABLE",
            "session": None,
            "network_sandbox_hub": network_hub,
        }

    state = load_state()
    sniff_cfg = dict(policy.get("packet_sniffing") or {})
    proc_corr = dict((sniff_cfg.get("process_correlation") or {}))
    hub_share = dict(((network_hub.get("share") or {}).get("share") or {}))
    network_hub_sid = str(hub_share.get("hub_session_id") or "")
    network_sandbox_sid = str(hub_share.get("sandbox_id") or f"app:{app_id}")
    session = {
        "session_id": sid,
        "app_id": str(app_id),
        "mode": mode,
        "internet_required": True,
        "expected_flow_profile": profile.get("expected_flow_profile"),
        "allowed_protocols": [str(x).lower() for x in profile.get("allowed_protocols", [])],
        "allowed_remote_ports": [int(x) for x in profile.get("allowed_remote_ports", [])],
        "allowed_remote_hosts": [str(x).lower() for x in profile.get("allowed_remote_hosts", [])],
        "allow_upload": bool(profile.get("allow_upload", False)),
        "allow_download": bool(profile.get("allow_download", False)),
        "web_download_write_guard_enabled": bool(web_guard_cfg.get("enabled", True)),
        "web_download_profile_id": str(web_guard_cfg.get("profile_id_default") or "p1"),
        "packet_rules_active": len(_active_packet_rules(policy)),
        "process_correlation_enabled": bool(proc_corr.get("enabled", True)),
        "process_correlation_require_pid_match": bool(proc_corr.get("require_pid_match", True)),
        "process_correlation_require_process_name_match": bool(proc_corr.get("require_process_name_match", True)),
        "process_correlation_require_session_tags": bool(proc_corr.get("require_session_tags", False)),
        "process_correlation_require_live_process_identity": bool(proc_corr.get("require_live_process_identity", True)),
        "process_correlation_require_correlated_stream": bool(
            sniff_cfg.get("require_correlated_stream_for_internet_required", True)
        ),
        "network_hub_session_id": network_hub_sid,
        "network_sandbox_id": network_sandbox_sid,
        "network_hub_enforced": True,
        "kernel_syscall_bridge_enabled": bool(sniff_cfg.get("kernel_syscall_bridge_enabled", True)),
        "qm_ecc_bridge_enabled": bool(sniff_cfg.get("qm_ecc_bridge_enabled", True)),
        "active": True,
        "quarantine_count": 0,
        "started_utc": _now_iso(),
        "last_seen_utc": _now_iso(),
        "profile_sandbox_ready": True,
    }
    state.setdefault("sessions", {})[sid] = session
    state["last_updated_utc"] = _now_iso()
    save_state(state)
    _audit(
        {
            "event": "firewall.session.started",
            "session_id": sid,
            "app_id": app_id,
            "mode": mode,
            "corr": corr,
            "network_hub_session_id": session.get("network_hub_session_id"),
            "network_sandbox_id": session.get("network_sandbox_id"),
        }
    )
    return {"ok": True, "code": "FIREWALL_GUARD_SESSION_ACTIVE", "session": session}


def _quarantine_packet(session: dict[str, Any], packet: dict[str, Any], reason: str, corr: str | None = None) -> str:
    app = _sanitize_token(str(session.get("app_id", "app")))
    sid = _sanitize_token(str(session.get("session_id", "session")))
    root = QUARANTINE_ROOT / app / sid
    root.mkdir(parents=True, exist_ok=True)
    name = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}_{_sanitize_token(reason)}.json"
    out = root / name
    obj = {"reason": reason, "session_id": session.get("session_id"), "app_id": session.get("app_id"), "packet": packet, "quarantined_utc": _now_iso()}
    out.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    _audit({"event": "firewall.packet.quarantined", "session_id": session.get("session_id"), "app_id": session.get("app_id"), "reason": reason, "path": str(out), "corr": corr})
    return str(out)


def inspect_packets(
    app_id: str,
    packets: list[dict[str, Any]],
    corr: str | None = None,
    session_id: str | None = None,
    expected_flow_profile: str | None = None,
    internet_hint: bool = False,
    correlation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packets = list(packets or [])
    policy = load_policy()
    state = load_state()
    session = None
    if session_id:
        session = (state.get("sessions") or {}).get(str(session_id))
    if not isinstance(session, dict):
        start = start_guard_session(app_id, corr=corr, internet_hint=internet_hint)
        session = start.get("session")
        if not isinstance(session, dict):
            return {"ok": bool(start.get("ok")), "code": start.get("code"), "session": session, "accepted": 0, "quarantined": 0, "quarantine_paths": []}
        state = load_state()
        session = (state.get("sessions") or {}).get(str(session.get("session_id")))
    if not isinstance(session, dict):
        return {"ok": False, "code": "FIREWALL_GUARD_SESSION_MISSING", "accepted": 0, "quarantined": 0, "quarantine_paths": []}

    if (not bool(session.get("internet_required", False))) and (not packets):
        return {"ok": True, "code": "FIREWALL_GUARD_NOT_REQUIRED", "session": session, "accepted": len(packets), "quarantined": 0, "quarantine_paths": []}

    mode = str(session.get("mode", "strict")).lower()
    expected_profile = str(expected_flow_profile or session.get("expected_flow_profile") or "").strip() or None
    allowed_protocols = [str(x).lower() for x in session.get("allowed_protocols", [])]
    allowed_ports = [int(x) for x in session.get("allowed_remote_ports", [])]
    allowed_hosts = [str(x).lower() for x in session.get("allowed_remote_hosts", [])]
    allow_upload = bool(session.get("allow_upload", False))
    allow_download = bool(session.get("allow_download", False))
    web_guard_cfg = _web_save_guard_cfg(policy)
    corr_obj = dict(correlation or {})
    expected_pid = _to_int_or_none(corr_obj.get("expected_pid"))
    expected_names = {
        str(x or "").strip().lower()
        for x in (corr_obj.get("expected_process_names") or [])
        if str(x or "").strip()
    }
    expected_capture_sid = str(corr_obj.get("capture_session_id") or "").strip()
    require_pid_match = bool(corr_obj.get("require_pid_match", False))
    require_session_tags = bool(corr_obj.get("require_session_tags", False))
    require_process_name_match = bool(corr_obj.get("require_process_name_match", False))
    require_expected_identity = bool(corr_obj.get("require_expected_identity", False))
    source = str(corr_obj.get("source", "") or "").strip().lower()
    correlated_stream = bool(corr_obj.get("correlated_stream", False)) or source == "process_bound_live"
    require_correlated_stream = bool(session.get("process_correlation_require_correlated_stream", False))
    has_correlation_expectations = bool(
        expected_pid is not None
        or expected_names
        or require_pid_match
        or require_session_tags
        or require_process_name_match
        or require_expected_identity
    )

    if require_expected_identity and correlated_stream and (expected_pid is None or not expected_names):
        reason = "FIREWALL_EXPECTED_IDENTITY_MISSING"
        synthetic_packet = {
            "direction": "egress",
            "flow_profile": expected_profile,
            "packet_source": source or "unknown",
            "app_id": app_id,
            "guard_session_id": str(session.get("session_id", "")),
            "capture_session_id": expected_capture_sid or None,
        }
        quarantine_path = _quarantine_packet(session, synthetic_packet, reason, corr=corr)
        sid = str(session.get("session_id"))
        session["last_seen_utc"] = _now_iso()
        session["quarantine_count"] = int(session.get("quarantine_count", 0)) + 1
        state.setdefault("sessions", {})[sid] = session
        state["quarantine_total"] = int(state.get("quarantine_total", 0)) + 1
        state["last_updated_utc"] = _now_iso()
        save_state(state)
        _increment_quarantine_counter(1)
        out = {
            "ok": False,
            "code": "FIREWALL_PACKET_QUARANTINED",
            "session": session,
            "accepted": 0,
            "quarantined": 1,
            "quarantine_paths": [quarantine_path],
            "findings": [
                {
                    "packet": synthetic_packet,
                    "verdict": "quarantined",
                    "reason": reason,
                    "matched_rule_id": None,
                    "matched_rule_effect": None,
                }
            ],
            "correlation": {
                "expected_pid": expected_pid,
                "expected_process_names": sorted(expected_names),
                "capture_session_id": expected_capture_sid or None,
                "require_pid_match": require_pid_match,
                "require_process_name_match": require_process_name_match,
                "require_session_tags": require_session_tags,
                "require_expected_identity": require_expected_identity,
                "source": source or None,
                "correlated_stream": correlated_stream,
                "require_correlated_stream": require_correlated_stream,
                "kernel_syscall_bridge_enabled": bool(session.get("kernel_syscall_bridge_enabled", True)),
            },
        }
        _audit(
            {
                "event": "firewall.inspect.completed",
                "session_id": sid,
                "app_id": app_id,
                "accepted": 0,
                "quarantined": 1,
                "corr": corr,
                "reason": reason,
            }
        )
        return out

    if not packets and require_correlated_stream and correlated_stream and has_correlation_expectations:
        reason = "FIREWALL_CORRELATED_STREAM_MISSING"
        synthetic_packet = {
            "direction": "egress",
            "flow_profile": expected_profile,
            "packet_source": source or "unknown",
            "app_id": app_id,
            "guard_session_id": str(session.get("session_id", "")),
            "capture_session_id": expected_capture_sid or None,
        }
        quarantine_path = _quarantine_packet(session, synthetic_packet, reason, corr=corr)
        sid = str(session.get("session_id"))
        session["last_seen_utc"] = _now_iso()
        session["quarantine_count"] = int(session.get("quarantine_count", 0)) + 1
        state.setdefault("sessions", {})[sid] = session
        state["quarantine_total"] = int(state.get("quarantine_total", 0)) + 1
        state["last_updated_utc"] = _now_iso()
        save_state(state)
        _increment_quarantine_counter(1)
        out = {
            "ok": False,
            "code": "FIREWALL_PACKET_QUARANTINED",
            "session": session,
            "accepted": 0,
            "quarantined": 1,
            "quarantine_paths": [quarantine_path],
            "findings": [
                {
                    "packet": synthetic_packet,
                    "verdict": "quarantined",
                    "reason": reason,
                    "matched_rule_id": None,
                    "matched_rule_effect": None,
                }
            ],
            "correlation": {
                "expected_pid": expected_pid,
                "expected_process_names": sorted(expected_names),
                "capture_session_id": expected_capture_sid or None,
                "require_pid_match": require_pid_match,
                "require_process_name_match": require_process_name_match,
                "require_session_tags": require_session_tags,
                "require_expected_identity": require_expected_identity,
                "source": source or None,
                "correlated_stream": correlated_stream,
                "require_correlated_stream": require_correlated_stream,
                "kernel_syscall_bridge_enabled": bool(session.get("kernel_syscall_bridge_enabled", True)),
            },
        }
        _audit(
            {
                "event": "firewall.inspect.completed",
                "session_id": sid,
                "app_id": app_id,
                "accepted": 0,
                "quarantined": 1,
                "corr": corr,
                "reason": reason,
            }
        )
        return out

    accepted = 0
    quarantined = 0
    paths: list[str] = []
    findings: list[dict[str, Any]] = []
    for pkt in packets:
        packet = dict(pkt or {})
        if not packet.get("network_sandbox_id"):
            packet["network_sandbox_id"] = str(session.get("network_sandbox_id") or "")
        if not packet.get("network_hub_session_id"):
            packet["network_hub_session_id"] = str(session.get("network_hub_session_id") or "")
        if not packet.get("ingress_adapter"):
            packet["ingress_adapter"] = "wired"
        direction = str(packet.get("direction", "egress")).lower()
        protocol = str(packet.get("protocol", "")).lower()
        host = str(packet.get("remote_host", "")).lower()
        port = int(packet.get("remote_port", 0) or 0)
        flow = str(packet.get("flow_profile", "")).strip() or None

        selected_rule = _select_packet_rule(policy, app_id, packet)
        reason = None
        matched_rule_id = None
        matched_rule_effect = None
        kernel_guard = None
        qm_ecc = None
        network_route = None
        transfer_type = _packet_transfer_type(packet)
        web_save_guard = None
        packet_pid = _to_int_or_none(packet.get("owning_pid"))
        packet_proc = str(packet.get("process_name", "") or "").strip().lower()
        packet_guard_sid = str(packet.get("guard_session_id", "") or "").strip()
        packet_capture_sid = str(packet.get("capture_session_id", "") or "").strip()

        if reason is None and (not bool(session.get("internet_required", False))) and direction == "egress":
            reason = "FIREWALL_INTERNET_NOT_PERMITTED"

        if reason is None and callable(evaluate_network_packet_route):
            network_route = evaluate_network_packet_route(app_id=str(app_id), packet=packet, corr=corr)
            if isinstance(network_route, dict) and not bool(network_route.get("ok", False)):
                reason = str(network_route.get("code") or "NETWORK_SANDBOX_ROUTE_BLOCKED")

        if reason is None and callable(quarantine_network_sandbox):
            infected_signal_fields = ["sandbox_infection_signal", "infected_sandbox", "malware_detected"]
            if callable(load_network_hub_policy):
                try:
                    cfg = dict(((load_network_hub_policy() or {}).get("quarantine") or {}))
                    configured = cfg.get("infected_signal_fields")
                    if isinstance(configured, list):
                        infected_signal_fields = [str(x).strip() for x in configured if str(x).strip()]
                except Exception:
                    infected_signal_fields = ["sandbox_infection_signal", "infected_sandbox", "malware_detected"]
            for sig_field in infected_signal_fields:
                if bool(packet.get(sig_field, False)):
                    target_sandbox = str(packet.get("network_sandbox_id") or session.get("network_sandbox_id") or f"app:{app_id}")
                    quarantine_network_sandbox(
                        sandbox_id=target_sandbox,
                        reason=f"INFECTION_SIGNAL:{sig_field}",
                        corr=corr,
                    )
                    reason = "NETWORK_SANDBOX_INFECTED_QUARANTINED"
                    break

        if expected_pid is not None:
            if packet_pid is None:
                if require_pid_match:
                    reason = "FIREWALL_PID_MISSING"
            elif packet_pid != expected_pid:
                reason = "FIREWALL_PID_MISMATCH"
        elif reason is None and require_pid_match:
            reason = "FIREWALL_EXPECTED_PID_MISSING"

        if reason is None and expected_names:
            if packet_proc:
                if packet_proc not in expected_names:
                    reason = "FIREWALL_PROCESS_MISMATCH"
            elif require_pid_match:
                reason = "FIREWALL_PROCESS_MISSING"
        elif reason is None and require_process_name_match:
            reason = "FIREWALL_EXPECTED_PROCESS_NAME_MISSING"

        if reason is None and expected_capture_sid:
            if packet_capture_sid:
                if packet_capture_sid != expected_capture_sid:
                    reason = "FIREWALL_CAPTURE_SESSION_MISMATCH"
            elif require_session_tags:
                reason = "FIREWALL_CAPTURE_SESSION_MISSING"

        if reason is None and session_id:
            sid_expected = str(session_id)
            if packet_guard_sid:
                if packet_guard_sid != sid_expected:
                    reason = "FIREWALL_GUARD_SESSION_MISMATCH"
            elif require_session_tags:
                reason = "FIREWALL_GUARD_SESSION_MISSING"

        if reason is None and transfer_type == "upload" and not allow_upload:
            reason = "FIREWALL_UPLOAD_NOT_PERMITTED"
        if reason is None and transfer_type == "download":
            if not allow_download:
                reason = "FIREWALL_DOWNLOAD_NOT_PERMITTED"
            elif _packet_web_origin(packet) and bool(web_guard_cfg.get("enabled", True)):
                save_path = _packet_download_target_path(packet)
                if callable(evaluate_web_download_target):
                    web_save_guard = evaluate_web_download_target(
                        save_path=save_path,
                        profile_id=str(packet.get("profile_id") or web_guard_cfg.get("profile_id_default") or "p1"),
                        allowed_folders=web_guard_cfg.get("allowed_profile_folders") or None,
                        require_target=bool(web_guard_cfg.get("require_target_path", True)),
                        require_profile_sandbox_target=bool(web_guard_cfg.get("require_profile_sandbox_target", True)),
                        deny_direct_c_root=bool(web_guard_cfg.get("deny_direct_c_root", True)),
                        required_vault_domains=web_guard_cfg.get("allowed_vault_domains") or None,
                        app_id=str(app_id),
                        corr=corr,
                    )
                    if isinstance(web_save_guard, dict) and not bool(web_save_guard.get("ok", False)):
                        reason = str(web_save_guard.get("code") or "PROFILE_SANDBOX_C_ROOT_BLOCKED")
                else:
                    reason = "FIREWALL_WEB_SAVE_GUARD_UNAVAILABLE"

        if isinstance(selected_rule, dict):
            matched_rule_id = str(selected_rule.get("id") or "firewall_rule")
            matched_rule_effect = _normalize_effect(str(selected_rule.get("effect", "deny")))
            if matched_rule_effect == "deny" and reason is None:
                reason = "FIREWALL_RULE_DENY"
            else:
                reason = reason

        if (
            reason is None
            and direction == "egress"
            and bool(session.get("kernel_syscall_bridge_enabled", True))
            and callable(kernel_guard_evaluate)
        ):
            kernel_guard = kernel_guard_evaluate(str(app_id), packet, corr=corr)
            if isinstance(kernel_guard, dict) and not bool(kernel_guard.get("ok")):
                reason = "FIREWALL_KERNEL_SYSCALL_DENY"

        if (
            reason is None
            and direction == "egress"
            and bool(session.get("qm_ecc_bridge_enabled", True))
            and callable(qm_ecc_evaluate_packet)
        ):
            qm_ecc = qm_ecc_evaluate_packet(packet, app_id=str(app_id), corr=corr)
            if isinstance(qm_ecc, dict) and not bool(qm_ecc.get("ok")):
                reason = "FIREWALL_QM_ECC_POLICY"

        if matched_rule_effect != "allow" and direction == "egress":
            if reason is None and allowed_protocols and protocol not in allowed_protocols:
                reason = "FIREWALL_PROTOCOL_MISMATCH"
            elif reason is None and allowed_ports and port not in allowed_ports:
                reason = "FIREWALL_PORT_MISMATCH"
            elif reason is None and allowed_hosts and not _is_host_allowed(host, allowed_hosts):
                reason = "FIREWALL_REMOTE_HOST_MISMATCH"
            elif reason is None and expected_profile and flow and flow != expected_profile:
                reason = "FIREWALL_FLOW_PROFILE_MISMATCH"

        if reason and mode == "strict":
            quarantined += 1
            paths.append(_quarantine_packet(session, packet, reason, corr=corr))
            findings.append(
                {
                    "packet": packet,
                    "verdict": "quarantined",
                    "reason": reason,
                    "matched_rule_id": matched_rule_id,
                    "matched_rule_effect": matched_rule_effect,
                    "transfer_type": transfer_type,
                    "network_route": network_route,
                    "web_save_guard": web_save_guard,
                    "kernel_guard": kernel_guard,
                    "qm_ecc": qm_ecc,
                }
            )
        else:
            accepted += 1
            findings.append(
                {
                    "packet": packet,
                    "verdict": "accepted",
                    "matched_rule_id": matched_rule_id,
                    "matched_rule_effect": matched_rule_effect,
                    "transfer_type": transfer_type,
                    "network_route": network_route,
                    "web_save_guard": web_save_guard,
                    "kernel_guard": kernel_guard,
                    "qm_ecc": qm_ecc,
                }
            )

    sid = str(session.get("session_id"))
    session["last_seen_utc"] = _now_iso()
    session["quarantine_count"] = int(session.get("quarantine_count", 0)) + quarantined
    state.setdefault("sessions", {})[sid] = session
    state["quarantine_total"] = int(state.get("quarantine_total", 0)) + quarantined
    state["last_updated_utc"] = _now_iso()
    save_state(state)
    _increment_quarantine_counter(quarantined)

    out = {
        "ok": quarantined == 0,
        "code": "FIREWALL_GUARD_OK" if quarantined == 0 else "FIREWALL_PACKET_QUARANTINED",
        "session": session,
        "accepted": accepted,
        "quarantined": quarantined,
        "quarantine_paths": paths,
        "findings": findings,
        "correlation": {
            "expected_pid": expected_pid,
            "expected_process_names": sorted(expected_names),
            "capture_session_id": expected_capture_sid or None,
            "require_pid_match": require_pid_match,
            "require_process_name_match": require_process_name_match,
            "require_session_tags": require_session_tags,
            "require_expected_identity": require_expected_identity,
            "source": source or None,
            "correlated_stream": correlated_stream,
            "require_correlated_stream": require_correlated_stream,
            "kernel_syscall_bridge_enabled": bool(session.get("kernel_syscall_bridge_enabled", True)),
        },
    }
    _audit(
        {
            "event": "firewall.inspect.completed",
            "session_id": sid,
            "app_id": app_id,
            "accepted": accepted,
            "quarantined": quarantined,
            "corr": corr,
        }
    )
    return out


def _quarantine_key(path: Path) -> str:
    try:
        return str(path.resolve())
    except Exception:
        return str(path)


def _iter_quarantine_files() -> list[Path]:
    if not QUARANTINE_ROOT.exists():
        return []
    out: list[Path] = []
    for path in QUARANTINE_ROOT.rglob("*.json"):
        if path.is_file():
            out.append(path)
    out.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return out


def _read_quarantine_record(path: Path) -> dict[str, Any] | None:
    try:
        obj = _load_json(path)
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    if not isinstance(obj.get("packet"), dict):
        obj["packet"] = {}
    return obj


def list_quarantine_packets(
    *,
    app_id: str | None = None,
    session_id: str | None = None,
    limit: int = 64,
    decision: str | None = None,
) -> dict[str, Any]:
    review_state = load_quarantine_review_state()
    reviews = dict(review_state.get("reviews") or {})
    app_filter = str(app_id or "").strip().lower()
    sid_filter = str(session_id or "").strip()
    decision_filter = str(decision or "").strip().lower()
    max_items = max(1, min(512, int(limit or 64)))

    rows: list[dict[str, Any]] = []
    for path in _iter_quarantine_files():
        obj = _read_quarantine_record(path)
        if obj is None:
            continue
        pkt = dict(obj.get("packet") or {})
        row_app = str(obj.get("app_id") or pkt.get("app_id") or "").strip()
        row_sid = str(obj.get("session_id") or pkt.get("guard_session_id") or "").strip()
        if app_filter and row_app.lower() != app_filter:
            continue
        if sid_filter and row_sid != sid_filter:
            continue

        review_key = _quarantine_key(path)
        review = dict(reviews.get(review_key) or {})
        review_decision = str(review.get("decision") or "pending").strip().lower()
        if decision_filter and review_decision != decision_filter:
            continue

        rows.append(
            {
                "path": str(path),
                "app_id": row_app or None,
                "session_id": row_sid or None,
                "reason": str(obj.get("reason") or "").strip() or None,
                "quarantined_utc": obj.get("quarantined_utc"),
                "packet": pkt,
                "review": {
                    "decision": review_decision,
                    "reviewed_utc": review.get("reviewed_utc"),
                    "reviewer": review.get("reviewer"),
                    "note": review.get("note"),
                    "allow_rule_id": review.get("allow_rule_id"),
                    "kernel_allow_rule_id": review.get("kernel_allow_rule_id"),
                },
            }
        )
        if len(rows) >= max_items:
            break

    return {
        "ok": True,
        "code": "FIREWALL_QUARANTINE_LIST_OK",
        "items": rows,
        "count": len(rows),
        "decision_filter": decision_filter or None,
    }


def _normalize_rule_port(packet: dict[str, Any]) -> int | None:
    try:
        raw = packet.get("remote_port")
        if raw is None:
            return None
        val = int(raw)
        if val < 0:
            return None
        return val
    except Exception:
        return None


def _allow_rule_from_quarantine(record: dict[str, Any], rule_id: str) -> dict[str, Any] | None:
    packet = dict(record.get("packet") or {})
    remote_host = str(packet.get("remote_host") or "").strip().lower()
    if not remote_host:
        return None
    app = str(record.get("app_id") or packet.get("app_id") or "*").strip().lower() or "*"
    direction = str(packet.get("direction") or "egress").strip().lower() or "egress"
    protocol = str(packet.get("protocol") or "").strip().lower()
    flow = str(packet.get("flow_profile") or "").strip()
    rule: dict[str, Any] = {
        "id": rule_id,
        "enabled": True,
        "source": "quarantine_adjudication",
        "app_id": app,
        "direction": direction,
        "effect": "allow",
        "remote_host": remote_host,
        "host_match": "exact",
        "priority": 2500,
    }
    if protocol:
        rule["protocol"] = protocol
    port = _normalize_rule_port(packet)
    if port is not None:
        rule["remote_port"] = int(port)
    if flow:
        rule["flow_profile"] = flow
    return rule


def _same_allow_rule(a: dict[str, Any], b: dict[str, Any]) -> bool:
    keys = ("app_id", "direction", "effect", "protocol", "remote_host", "host_match", "remote_port", "flow_profile")
    for k in keys:
        if str(a.get(k) if a.get(k) is not None else "") != str(b.get(k) if b.get(k) is not None else ""):
            return False
    return str(a.get("effect", "")).lower() == "allow"


def _next_quarantine_rule_id(policy: dict[str, Any]) -> str:
    existing = set()
    for item in policy.get("packet_rules", []):
        if isinstance(item, dict):
            rid = str(item.get("id") or "").strip()
            if rid:
                existing.add(rid)
    for idx in range(1, 100000):
        rid = f"allow_quarantine_{idx:05d}"
        if rid not in existing:
            return rid
    return f"allow_quarantine_{secrets.token_hex(4)}"


def adjudicate_quarantine_packet(
    *,
    path: str,
    decision: str,
    reviewer: str = "security_host",
    note: str | None = None,
    corr: str | None = None,
) -> dict[str, Any]:
    p = Path(str(path or "").strip())
    if not p.exists():
        return {"ok": False, "code": "FIREWALL_QUARANTINE_PATH_MISSING", "path": str(p)}
    record = _read_quarantine_record(p)
    if record is None:
        return {"ok": False, "code": "FIREWALL_QUARANTINE_RECORD_INVALID", "path": str(p)}

    dec = str(decision or "").strip().lower()
    if dec not in ("dismiss", "allow_rule"):
        return {"ok": False, "code": "FIREWALL_QUARANTINE_DECISION_INVALID", "decision": decision}

    review_state = load_quarantine_review_state()
    reviews = dict(review_state.get("reviews") or {})
    review_key = _quarantine_key(p)
    allow_rule_id = None
    allow_rule = None
    kernel_allow_rule_id = None

    if dec == "allow_rule":
        policy = load_policy()
        rules = list(policy.get("packet_rules", []))
        if not isinstance(rules, list):
            rules = []
        candidate_id = _next_quarantine_rule_id(policy)
        candidate = _allow_rule_from_quarantine(record, candidate_id)
        if candidate is None:
            return {"ok": False, "code": "FIREWALL_QUARANTINE_RULE_UNDER_SPECIFIED", "path": str(p)}
        for existing in rules:
            if not isinstance(existing, dict):
                continue
            if _same_allow_rule(existing, candidate):
                allow_rule_id = str(existing.get("id") or "")
                allow_rule = dict(existing)
                break
        if allow_rule is None:
            rules.append(candidate)
            policy["packet_rules"] = rules
            _save_json(POLICY_PATH, policy)
            allow_rule_id = candidate["id"]
            allow_rule = candidate
        if callable(add_allow_rule_for_packet):
            kernel_result = add_allow_rule_for_packet(
                str(record.get("app_id") or ""),
                dict(record.get("packet") or {}),
                note=str(note or "").strip() or None,
                corr=corr,
            )
            if isinstance(kernel_result, dict):
                kernel_allow_rule_id = str(kernel_result.get("rule_id") or "") or None

    review = {
        "decision": dec,
        "reviewed_utc": _now_iso(),
        "reviewer": str(reviewer or "security_host"),
        "note": str(note or "").strip() or None,
        "allow_rule_id": allow_rule_id,
        "kernel_allow_rule_id": kernel_allow_rule_id,
    }
    reviews[review_key] = review
    review_state["reviews"] = reviews
    review_state["last_updated_utc"] = _now_iso()
    save_quarantine_review_state(review_state)
    _audit(
        {
            "event": "firewall.quarantine.adjudicated",
            "path": str(p),
            "decision": dec,
            "allow_rule_id": allow_rule_id,
            "kernel_allow_rule_id": kernel_allow_rule_id,
            "corr": corr,
        }
    )
    return {
        "ok": True,
        "code": "FIREWALL_QUARANTINE_ADJUDICATED",
        "path": str(p),
        "review": review,
        "allow_rule": allow_rule,
    }


def replay_quarantine_packet(
    *,
    path: str,
    corr: str | None = None,
    expected_flow_profile: str | None = None,
) -> dict[str, Any]:
    p = Path(str(path or "").strip())
    if not p.exists():
        return {"ok": False, "code": "FIREWALL_QUARANTINE_PATH_MISSING", "path": str(p)}
    record = _read_quarantine_record(p)
    if record is None:
        return {"ok": False, "code": "FIREWALL_QUARANTINE_RECORD_INVALID", "path": str(p)}

    packet = dict(record.get("packet") or {})
    app_id = str(record.get("app_id") or packet.get("app_id") or "external_installer")
    session_id = str(record.get("session_id") or packet.get("guard_session_id") or "").strip() or None
    flow_profile = str(expected_flow_profile or packet.get("flow_profile") or "").strip() or None

    result = inspect_packets(
        app_id=app_id,
        packets=[packet],
        corr=corr,
        session_id=session_id,
        expected_flow_profile=flow_profile,
        internet_hint=True,
    )
    _audit(
        {
            "event": "firewall.quarantine.replayed",
            "path": str(p),
            "ok": bool(result.get("ok")),
            "quarantined": int(result.get("quarantined", 0) or 0),
            "corr": corr,
        }
    )
    return {
        "ok": bool(result.get("ok")),
        "code": "FIREWALL_QUARANTINE_REPLAY_OK" if bool(result.get("ok")) else "FIREWALL_QUARANTINE_REPLAY_BLOCKED",
        "path": str(p),
        "result": result,
    }
