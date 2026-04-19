from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

SECURITY_DIR = Path(axion_path_str("runtime", "security"))
if str(SECURITY_DIR) not in sys.path:
    sys.path.append(str(SECURITY_DIR))

from firewall_guard import inspect_packets

CODES = {
    "FIREWALL_PACKET_QUARANTINED": 3601,
    "FIREWALL_FLOW_PROFILE_MISMATCH": 3602,
    "FIREWALL_RULE_PRECEDENCE_BROKEN": 3603,
    "FIREWALL_PID_CORRELATION_ENFORCED": 3604,
    "FIREWALL_CORRELATED_STREAM_REQUIRED": 3605,
}


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


base = axion_path_str("out", "runtime")
os.makedirs(base, exist_ok=True)
audit_p = os.path.join(base, "firewall_guard_integrity_audit.json")
smoke_p = os.path.join(base, "firewall_guard_integrity_smoke.json")
mode = "pass"
if len(sys.argv) > 1:
    mode = sys.argv[1]
policy_path = axion_path("config", "FIREWALL_GUARD_POLICY_V1.json")
original_policy_raw = policy_path.read_text(encoding="utf-8-sig") if policy_path.exists() else None

packets = [
    {
        "direction": "egress",
        "protocol": "https",
        "remote_host": "repo.axion.local",
        "remote_port": 443,
        "flow_profile": "installer_update",
    }
]
if mode == "unauthorized_host":
    packets = [
        {
            "direction": "egress",
            "protocol": "https",
            "remote_host": "rogue.example.net",
            "remote_port": 443,
            "flow_profile": "installer_update",
        }
    ]
elif mode == "flow_mismatch":
    packets = [
        {
            "direction": "egress",
            "protocol": "https",
            "remote_host": "repo.axion.local",
            "remote_port": 443,
            "flow_profile": "unexpected_flow",
        }
    ]
elif mode == "rule_precedence":
    packets = [
        {
            "direction": "egress",
            "protocol": "https",
            "remote_host": "repo.axion.local",
            "remote_port": 443,
            "flow_profile": "installer_update",
        }
    ]
    if policy_path.exists():
        policy_obj = json.loads(original_policy_raw)
        policy_obj["packet_rules"] = [
            {
                "id": "allow_axion_wildcard",
                "app_id": "external_installer",
                "direction": "egress",
                "effect": "allow",
                "remote_host": "*.axion.local",
                "host_match": "wildcard",
                "priority": 100
            },
            {
                "id": "deny_repo_exact",
                "app_id": "external_installer",
                "direction": "egress",
                "effect": "deny",
                "remote_host": "repo.axion.local",
                "host_match": "exact",
                "priority": 100
            }
        ]
        policy_path.write_text(json.dumps(policy_obj, indent=2) + "\n", encoding="utf-8")
elif mode == "pid_mismatch":
    packets = [
        {
            "direction": "egress",
            "protocol": "https",
            "remote_host": "repo.axion.local",
            "remote_port": 443,
            "flow_profile": "installer_update",
            "owning_pid": 111,
            "process_name": "python",
            "guard_session_id": "guard-sample",
        }
    ]
elif mode == "correlated_stream_missing":
    packets = []

try:
    res = inspect_packets(
        app_id="external_installer",
        packets=packets,
        corr="corr_firewall_guard_integrity_001",
        expected_flow_profile="installer_update",
        internet_hint=True,
        correlation=(
            {
                "expected_pid": 222,
                "expected_process_names": ["python"],
                "require_pid_match": True,
                "source": "process_bound_live",
                "correlated_stream": True,
            }
            if mode == "pid_mismatch"
            else {
                "expected_pid": 222,
                "expected_process_names": ["python"],
                "require_pid_match": True,
                "source": "process_bound_live",
                "correlated_stream": True,
            }
            if mode == "correlated_stream_missing"
            else None
        ),
    )
finally:
    if mode == "rule_precedence" and original_policy_raw is not None:
        policy_path.write_text(original_policy_raw, encoding="utf-8")

failures = []
if mode == "unauthorized_host" and res.get("quarantined", 0) > 0:
    failures = [{"code": "FIREWALL_PACKET_QUARANTINED", "detail": "quarantined unauthorized destination packet"}]
elif mode == "flow_mismatch" and res.get("quarantined", 0) > 0:
    failures = [{"code": "FIREWALL_FLOW_PROFILE_MISMATCH", "detail": "quarantined flow profile mismatch"}]
elif mode == "rule_precedence" and res.get("quarantined", 0) > 0:
    reason = ""
    findings = res.get("findings", [])
    if findings and isinstance(findings[0], dict):
        reason = str(findings[0].get("reason", ""))
    if reason == "FIREWALL_RULE_DENY":
        failures = [{"code": "FIREWALL_RULE_PRECEDENCE_BROKEN", "detail": "deny exact rule enforced over wildcard allow (negative control)"}]
    else:
        failures = [{"code": "FIREWALL_RULE_PRECEDENCE_BROKEN", "detail": f"unexpected deny reason: {reason}"}]
elif mode == "pid_mismatch" and res.get("quarantined", 0) > 0:
    reason = ""
    findings = res.get("findings", [])
    if findings and isinstance(findings[0], dict):
        reason = str(findings[0].get("reason", ""))
    if reason == "FIREWALL_PID_MISMATCH":
        failures = [{"code": "FIREWALL_PID_CORRELATION_ENFORCED", "detail": "pid correlation mismatch quarantined"}]
    else:
        failures = [{"code": "FIREWALL_PID_CORRELATION_ENFORCED", "detail": f"unexpected correlation reason: {reason}"}]
elif mode == "correlated_stream_missing" and res.get("quarantined", 0) > 0:
    reason = ""
    findings = res.get("findings", [])
    if findings and isinstance(findings[0], dict):
        reason = str(findings[0].get("reason", ""))
    if reason == "FIREWALL_CORRELATED_STREAM_MISSING":
        failures = [{"code": "FIREWALL_CORRELATED_STREAM_REQUIRED", "detail": "missing correlated stream was quarantined"}]
    else:
        failures = [{"code": "FIREWALL_CORRELATED_STREAM_REQUIRED", "detail": f"unexpected stream reason: {reason}"}]
elif mode != "pass" and res.get("quarantined", 0) == 0:
    failures = [{"code": "FIREWALL_PACKET_QUARANTINED", "detail": "expected quarantine did not occur"}]

status = "FAIL" if failures else "PASS"
smoke = {"timestamp_utc": now(), "status": status, "result": res, "failures": failures}
audit = {
    "timestamp_utc": now(),
    "status": status,
    "checks": ["guard_session_active", "packet_sniffing_metadata", "quarantine_on_mismatch"],
    "result": res,
    "failures": failures,
}
json.dump(smoke, open(smoke_p, "w", encoding="utf-8"), indent=2)
json.dump(audit, open(audit_p, "w", encoding="utf-8"), indent=2)
if failures:
    raise SystemExit(CODES[failures[0]["code"]])
