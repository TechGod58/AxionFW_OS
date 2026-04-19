from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AXION_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = AXION_ROOT / "config" / "KERNEL_NETWORK_SYSCALL_GUARD_V1.json"
AUDIT_PATH = AXION_ROOT / "data" / "audit" / "kernel_syscall_guard.ndjson"


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
    if not POLICY_PATH.exists():
        return {"version": 1, "policyId": "AXION_KERNEL_NETWORK_SYSCALL_GUARD_V1", "enabled": False, "default_effect": "allow", "rules": []}
    try:
        obj = _load_json(POLICY_PATH)
    except Exception:
        return {"version": 1, "policyId": "AXION_KERNEL_NETWORK_SYSCALL_GUARD_V1", "enabled": False, "default_effect": "allow", "rules": []}
    if not isinstance(obj, dict):
        return {"version": 1, "policyId": "AXION_KERNEL_NETWORK_SYSCALL_GUARD_V1", "enabled": False, "default_effect": "allow", "rules": []}
    if not isinstance(obj.get("rules"), list):
        obj["rules"] = []
    if str(obj.get("default_effect") or "").strip().lower() not in ("allow", "deny"):
        obj["default_effect"] = "deny"
    obj.setdefault("enabled", True)
    return obj


def _to_int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _normalize_host_mode(host: str, mode: str | None) -> str:
    m = str(mode or "").strip().lower()
    if m in ("exact", "suffix", "wildcard"):
        return m
    if str(host or "").strip().startswith("*."):
        return "wildcard"
    return "exact"


def _host_match(host: str, rule_host: str, host_mode: str | None) -> bool:
    h = str(host or "").strip().lower()
    r = str(rule_host or "").strip().lower()
    if not h or not r:
        return False
    mode = _normalize_host_mode(r, host_mode)
    if mode == "exact":
        return h == r
    if mode == "suffix":
        return h.endswith(r)
    if r.startswith("*."):
        return h.endswith(r[1:])
    return h == r


def _rule_matches(rule: dict[str, Any], app_id: str, packet: dict[str, Any]) -> bool:
    app_sel = str(rule.get("app_id", "*") or "*").strip().lower()
    if app_sel not in ("*", str(app_id or "").strip().lower()):
        return False
    protocol = str(packet.get("protocol", "") or "").strip().lower()
    rule_protocol = str(rule.get("protocol", "") or "").strip().lower()
    if rule_protocol and rule_protocol != protocol:
        return False
    pkt_port = _to_int_or_none(packet.get("remote_port"))
    rule_port = _to_int_or_none(rule.get("remote_port"))
    if rule_port is not None and pkt_port != rule_port:
        return False
    rule_host = str(rule.get("remote_host", "") or "").strip().lower()
    if rule_host and not _host_match(str(packet.get("remote_host", "")), rule_host, rule.get("host_match")):
        return False
    return True


def _rule_specificity(rule: dict[str, Any]) -> int:
    score = 0
    app_sel = str(rule.get("app_id", "*") or "*").strip().lower()
    if app_sel and app_sel != "*":
        score += 100
    if str(rule.get("protocol", "") or "").strip():
        score += 20
    if _to_int_or_none(rule.get("remote_port")) is not None:
        score += 20
    if str(rule.get("remote_host", "") or "").strip():
        mode = _normalize_host_mode(str(rule.get("remote_host", "") or ""), rule.get("host_match"))
        score += 24 if mode == "exact" else 16
    return score


def _rule_priority(rule: dict[str, Any]) -> int:
    try:
        return int(rule.get("priority", 0) or 0)
    except Exception:
        return 0


def evaluate_packet(app_id: str, packet: dict[str, Any], corr: str | None = None) -> dict[str, Any]:
    policy = load_policy()
    if not bool(policy.get("enabled", True)):
        return {"ok": True, "code": "KERNEL_NET_GUARD_DISABLED", "effect": "allow", "rule_id": None}

    candidates: list[tuple[int, int, int, dict[str, Any]]] = []
    for item in policy.get("rules", []):
        if not isinstance(item, dict):
            continue
        if not bool(item.get("enabled", True)):
            continue
        if not _rule_matches(item, app_id, packet):
            continue
        effect = str(item.get("effect", "deny") or "deny").strip().lower()
        deny_rank = 1 if effect == "deny" else 0
        candidates.append((_rule_specificity(item), _rule_priority(item), deny_rank, item))

    effect = str(policy.get("default_effect", "deny") or "deny").strip().lower()
    rule_id = None
    if candidates:
        candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
        best = candidates[0][3]
        effect = str(best.get("effect", "deny") or "deny").strip().lower()
        rule_id = str(best.get("id") or "")

    allowed = effect == "allow"
    out = {
        "ok": allowed,
        "code": "KERNEL_NET_GUARD_ALLOW" if allowed else "KERNEL_NET_GUARD_DENY",
        "effect": "allow" if allowed else "deny",
        "rule_id": rule_id,
    }
    _audit(
        {
            "event": "kernel.net_guard.decision",
            "app_id": app_id,
            "protocol": packet.get("protocol"),
            "remote_host": packet.get("remote_host"),
            "remote_port": packet.get("remote_port"),
            "effect": out["effect"],
            "rule_id": rule_id,
            "corr": corr,
        }
    )
    return out


def add_allow_rule_for_packet(app_id: str, packet: dict[str, Any], note: str | None = None, corr: str | None = None) -> dict[str, Any]:
    host = str(packet.get("remote_host") or "").strip().lower()
    if not host:
        return {"ok": False, "code": "KERNEL_NET_GUARD_RULE_UNDER_SPECIFIED"}
    policy = load_policy()
    rules = list(policy.get("rules", []))
    if not isinstance(rules, list):
        rules = []
    remote_port = _to_int_or_none(packet.get("remote_port"))
    protocol = str(packet.get("protocol") or "").strip().lower()

    candidate = {
        "id": None,
        "enabled": True,
        "source": "firewall_quarantine_adjudication",
        "note": str(note or "").strip() or None,
        "app_id": str(app_id or "*").strip().lower() or "*",
        "effect": "allow",
        "protocol": protocol,
        "remote_host": host,
        "host_match": "exact",
        "priority": 2500,
    }
    if remote_port is not None:
        candidate["remote_port"] = int(remote_port)

    for item in rules:
        if not isinstance(item, dict):
            continue
        if str(item.get("effect", "")).strip().lower() != "allow":
            continue
        if str(item.get("app_id", "")).strip().lower() != candidate["app_id"]:
            continue
        if str(item.get("protocol", "")).strip().lower() != candidate["protocol"]:
            continue
        if str(item.get("remote_host", "")).strip().lower() != candidate["remote_host"]:
            continue
        if int(_to_int_or_none(item.get("remote_port")) or 0) != int(remote_port or 0):
            continue
        return {"ok": True, "code": "KERNEL_NET_GUARD_RULE_EXISTS", "rule_id": str(item.get("id") or "")}

    existing_ids = {str((x or {}).get("id") or "").strip() for x in rules if isinstance(x, dict)}
    rid = None
    for idx in range(1, 100000):
        probe = f"kernel_allow_quarantine_{idx:05d}"
        if probe not in existing_ids:
            rid = probe
            break
    if rid is None:
        rid = f"kernel_allow_quarantine_fallback"
    candidate["id"] = rid
    rules.append(candidate)
    policy["rules"] = rules
    _save_json(POLICY_PATH, policy)
    _audit({"event": "kernel.net_guard.rule_added", "rule_id": rid, "app_id": candidate["app_id"], "corr": corr})
    return {"ok": True, "code": "KERNEL_NET_GUARD_RULE_ADDED", "rule_id": rid}
