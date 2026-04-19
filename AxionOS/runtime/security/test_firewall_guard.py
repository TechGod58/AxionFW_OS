import json
from pathlib import Path

from firewall_guard import (
    POLICY_PATH,
    inspect_packets,
    start_guard_session,
    list_quarantine_packets,
    adjudicate_quarantine_packet,
    replay_quarantine_packet,
)
from profile_sandbox_guard import ensure_profile_sandbox_storage
from network_sandbox_hub import share_internet_to_sandbox

AXION_ROOT = Path(__file__).resolve().parents[2]


def _set_policy_packet_rules(rules):
    obj = json.loads(POLICY_PATH.read_text(encoding="utf-8-sig"))
    obj["packet_rules"] = list(rules)
    POLICY_PATH.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def test_firewall_guard_allows_expected_installer_traffic():
    start = start_guard_session("external_installer", corr="corr_fw_001", internet_hint=True)
    assert start["ok"] is True
    sid = start["session"]["session_id"]

    result = inspect_packets(
        app_id="external_installer",
        session_id=sid,
        expected_flow_profile="installer_update",
        packets=[
            {
                "direction": "egress",
                "protocol": "https",
                "remote_host": "repo.axion.local",
                "remote_port": 443,
                "flow_profile": "installer_update",
            }
        ],
        corr="corr_fw_002",
        internet_hint=True,
    )
    assert result["ok"] is True
    assert result["quarantined"] == 0


def test_firewall_guard_quarantines_mismatched_packet():
    start = start_guard_session("external_installer", corr="corr_fw_003", internet_hint=True)
    assert start["ok"] is True
    sid = start["session"]["session_id"]

    result = inspect_packets(
        app_id="external_installer",
        session_id=sid,
        expected_flow_profile="installer_update",
        packets=[
            {
                "direction": "egress",
                "protocol": "tcp",
                "remote_host": "evil.example.net",
                "remote_port": 443,
                "flow_profile": "installer_update",
            }
        ],
        corr="corr_fw_004",
        internet_hint=True,
    )
    assert result["ok"] is False
    assert result["code"] == "FIREWALL_PACKET_QUARANTINED"
    assert result["quarantined"] == 1
    assert len(result["quarantine_paths"]) == 1


def test_firewall_rule_exact_allow_beats_wildcard_deny():
    original_policy = POLICY_PATH.read_text(encoding="utf-8-sig")
    try:
        _set_policy_packet_rules(
            [
                {
                    "id": "deny_axion_wildcard",
                    "app_id": "external_installer",
                    "direction": "egress",
                    "effect": "deny",
                    "remote_host": "*.axion.local",
                    "host_match": "wildcard",
                    "priority": 100,
                },
                {
                    "id": "allow_repo_exact",
                    "app_id": "external_installer",
                    "direction": "egress",
                    "effect": "allow",
                    "remote_host": "repo.axion.local",
                    "host_match": "exact",
                    "priority": 100,
                },
            ]
        )

        start = start_guard_session("external_installer", corr="corr_fw_005", internet_hint=True)
        sid = start["session"]["session_id"]
        result = inspect_packets(
            app_id="external_installer",
            session_id=sid,
            expected_flow_profile="installer_update",
            packets=[
                {
                    "direction": "egress",
                    "protocol": "https",
                    "remote_host": "repo.axion.local",
                    "remote_port": 443,
                    "flow_profile": "installer_update",
                }
            ],
            corr="corr_fw_006",
            internet_hint=True,
        )
        assert result["ok"] is True
        assert result["quarantined"] == 0
        assert result["findings"][0]["matched_rule_id"] == "allow_repo_exact"
        assert result["findings"][0]["matched_rule_effect"] == "allow"
    finally:
        POLICY_PATH.write_text(original_policy, encoding="utf-8")


def test_firewall_rule_deny_wins_on_equal_specificity():
    original_policy = POLICY_PATH.read_text(encoding="utf-8-sig")
    try:
        _set_policy_packet_rules(
            [
                {
                    "id": "allow_repo_exact",
                    "app_id": "external_installer",
                    "direction": "egress",
                    "effect": "allow",
                    "remote_host": "repo.axion.local",
                    "host_match": "exact",
                    "priority": 100,
                },
                {
                    "id": "deny_repo_exact",
                    "app_id": "external_installer",
                    "direction": "egress",
                    "effect": "deny",
                    "remote_host": "repo.axion.local",
                    "host_match": "exact",
                    "priority": 100,
                },
            ]
        )

        start = start_guard_session("external_installer", corr="corr_fw_007", internet_hint=True)
        sid = start["session"]["session_id"]
        result = inspect_packets(
            app_id="external_installer",
            session_id=sid,
            expected_flow_profile="installer_update",
            packets=[
                {
                    "direction": "egress",
                    "protocol": "https",
                    "remote_host": "repo.axion.local",
                    "remote_port": 443,
                    "flow_profile": "installer_update",
                }
            ],
            corr="corr_fw_008",
            internet_hint=True,
        )
        assert result["ok"] is False
        assert result["code"] == "FIREWALL_PACKET_QUARANTINED"
        assert result["quarantined"] == 1
        assert result["findings"][0]["reason"] == "FIREWALL_RULE_DENY"
        assert result["findings"][0]["matched_rule_id"] == "deny_repo_exact"
        assert result["findings"][0]["matched_rule_effect"] == "deny"
    finally:
        POLICY_PATH.write_text(original_policy, encoding="utf-8")


def test_firewall_correlation_pid_mismatch_quarantines():
    start = start_guard_session("external_installer", corr="corr_fw_009", internet_hint=True)
    assert start["ok"] is True
    sid = start["session"]["session_id"]

    result = inspect_packets(
        app_id="external_installer",
        session_id=sid,
        expected_flow_profile="installer_update",
        packets=[
            {
                "direction": "egress",
                "protocol": "https",
                "remote_host": "repo.axion.local",
                "remote_port": 443,
                "flow_profile": "installer_update",
                "owning_pid": 777,
                "process_name": "python",
                "guard_session_id": sid,
            }
        ],
        corr="corr_fw_010",
        internet_hint=True,
        correlation={
            "expected_pid": 888,
            "expected_process_names": ["python"],
            "require_pid_match": True,
            "require_session_tags": True,
        },
    )
    assert result["ok"] is False
    assert result["code"] == "FIREWALL_PACKET_QUARANTINED"
    assert result["quarantined"] == 1
    assert result["findings"][0]["reason"] == "FIREWALL_PID_MISMATCH"


def test_firewall_correlation_guard_session_mismatch_quarantines():
    start = start_guard_session("external_installer", corr="corr_fw_011", internet_hint=True)
    assert start["ok"] is True
    sid = start["session"]["session_id"]

    result = inspect_packets(
        app_id="external_installer",
        session_id=sid,
        expected_flow_profile="installer_update",
        packets=[
            {
                "direction": "egress",
                "protocol": "https",
                "remote_host": "repo.axion.local",
                "remote_port": 443,
                "flow_profile": "installer_update",
                "owning_pid": 888,
                "process_name": "python",
                "guard_session_id": "guard-other",
                "capture_session_id": "proj-001",
            }
        ],
        corr="corr_fw_012",
        internet_hint=True,
        correlation={
            "expected_pid": 888,
            "expected_process_names": ["python"],
            "capture_session_id": "proj-001",
            "require_pid_match": True,
            "require_session_tags": True,
        },
    )
    assert result["ok"] is False
    assert result["code"] == "FIREWALL_PACKET_QUARANTINED"
    assert result["quarantined"] == 1
    assert result["findings"][0]["reason"] == "FIREWALL_GUARD_SESSION_MISMATCH"


def test_firewall_correlation_missing_stream_quarantines():
    start = start_guard_session("external_installer", corr="corr_fw_013", internet_hint=True)
    assert start["ok"] is True
    sid = start["session"]["session_id"]

    result = inspect_packets(
        app_id="external_installer",
        session_id=sid,
        expected_flow_profile="installer_update",
        packets=[],
        corr="corr_fw_014",
        internet_hint=True,
        correlation={
            "expected_pid": 9999,
            "expected_process_names": ["python"],
            "require_pid_match": True,
            "source": "process_bound_live",
            "correlated_stream": True,
        },
    )
    assert result["ok"] is False
    assert result["code"] == "FIREWALL_PACKET_QUARANTINED"
    assert result["quarantined"] == 1
    assert result["findings"][0]["reason"] == "FIREWALL_CORRELATED_STREAM_MISSING"


def test_firewall_live_expected_identity_missing_quarantines():
    start = start_guard_session("external_installer", corr="corr_fw_015", internet_hint=True)
    assert start["ok"] is True
    sid = start["session"]["session_id"]

    result = inspect_packets(
        app_id="external_installer",
        session_id=sid,
        expected_flow_profile="installer_update",
        packets=[
            {
                "direction": "egress",
                "protocol": "https",
                "remote_host": "repo.axion.local",
                "remote_port": 443,
                "flow_profile": "installer_update",
            }
        ],
        corr="corr_fw_016",
        internet_hint=True,
        correlation={
            "source": "process_bound_live",
            "correlated_stream": True,
            "execution_live": True,
            "require_expected_identity": True,
            "require_pid_match": True,
            "require_process_name_match": True,
        },
    )
    assert result["ok"] is False
    assert result["code"] == "FIREWALL_PACKET_QUARANTINED"
    assert result["findings"][0]["reason"] == "FIREWALL_EXPECTED_IDENTITY_MISSING"


def test_firewall_quarantine_adjudication_allow_rule_then_replay_ok():
    qdir = Path(POLICY_PATH.parents[1] / "data" / "quarantine" / "network_packets" / "external_installer" / "adjudication-unit")
    qdir.mkdir(parents=True, exist_ok=True)
    qpath = str(qdir / "20260417T000000000200Z_test.json")
    Path(qpath).write_text(
        json.dumps(
            {
                "reason": "FIREWALL_REMOTE_HOST_MISMATCH",
                "session_id": "adjudication-unit",
                "app_id": "external_installer",
                "packet": {
                    "direction": "egress",
                    "protocol": "https",
                    "remote_host": "adjudication-test.example.net",
                    "remote_port": 443,
                    "flow_profile": "installer_update",
                },
                "quarantined_utc": "2026-04-17T00:00:00Z",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    listing = list_quarantine_packets(app_id="external_installer", limit=50)
    assert listing["ok"] is True
    assert any(str(x.get("path")) == qpath for x in listing.get("items", []))

    reviewed = adjudicate_quarantine_packet(path=qpath, decision="allow_rule", note="unit test allow", corr="corr_fw_017")
    assert reviewed["ok"] is True
    assert (reviewed.get("review") or {}).get("decision") == "allow_rule"
    assert ((reviewed.get("allow_rule") or {}).get("id"))
    assert ((reviewed.get("review") or {}).get("kernel_allow_rule_id"))

    replayed = replay_quarantine_packet(path=qpath, corr="corr_fw_018")
    assert replayed["ok"] is True
    assert replayed["code"] == "FIREWALL_QUARANTINE_REPLAY_OK"


def test_firewall_kernel_syscall_bridge_can_quarantine(monkeypatch):
    def _deny_kernel(_app_id, _packet, corr=None):
        return {"ok": False, "code": "KERNEL_NET_GUARD_DENY", "effect": "deny", "rule_id": "deny-test"}

    monkeypatch.setattr("firewall_guard.kernel_guard_evaluate", _deny_kernel)
    start = start_guard_session("external_installer", corr="corr_fw_019", internet_hint=True)
    sid = start["session"]["session_id"]
    result = inspect_packets(
        app_id="external_installer",
        session_id=sid,
        expected_flow_profile="installer_update",
        packets=[
            {
                "direction": "egress",
                "protocol": "https",
                "remote_host": "repo.axion.local",
                "remote_port": 443,
                "flow_profile": "installer_update",
            }
        ],
        corr="corr_fw_020",
        internet_hint=True,
    )
    assert result["ok"] is False
    assert result["code"] == "FIREWALL_PACKET_QUARANTINED"
    assert result["findings"][0]["reason"] == "FIREWALL_KERNEL_SYSCALL_DENY"


def test_firewall_qm_ecc_bridge_can_quarantine(monkeypatch):
    monkeypatch.setattr(
        "firewall_guard.kernel_guard_evaluate",
        lambda _app_id, _packet, corr=None: {"ok": True, "code": "KERNEL_NET_GUARD_ALLOW", "effect": "allow", "rule_id": "allow-test"},
    )
    start = start_guard_session("external_installer", corr="corr_fw_021", internet_hint=True)
    sid = start["session"]["session_id"]
    result = inspect_packets(
        app_id="external_installer",
        session_id=sid,
        expected_flow_profile="installer_update",
        packets=[
            {
                "direction": "egress",
                "protocol": "https",
                "remote_host": "repo.axion.local",
                "remote_port": 443,
                "flow_profile": "installer_update",
                "qm_force_action": "halt",
                "ecc_error_rate": 0.95,
                "instability": 0.95,
            }
        ],
        corr="corr_fw_022",
        internet_hint=True,
    )
    assert result["ok"] is False
    assert result["code"] == "FIREWALL_PACKET_QUARANTINED"
    assert result["findings"][0]["reason"] == "FIREWALL_QM_ECC_POLICY"


def test_firewall_upload_without_permission_quarantines():
    start = start_guard_session("external_installer", corr="corr_fw_023", internet_hint=True)
    assert start["ok"] is True
    sid = start["session"]["session_id"]

    result = inspect_packets(
        app_id="external_installer",
        session_id=sid,
        expected_flow_profile="installer_update",
        packets=[
            {
                "direction": "egress",
                "protocol": "https",
                "remote_host": "repo.axion.local",
                "remote_port": 443,
                "flow_profile": "installer_update",
                "transfer_type": "upload",
                "origin": "web",
                "save_path": str(AXION_ROOT / "data" / "profiles" / "p1" / "Downloads" / "upload.bin"),
            }
        ],
        corr="corr_fw_024",
        internet_hint=True,
    )
    assert result["ok"] is False
    assert result["code"] == "FIREWALL_PACKET_QUARANTINED"
    assert result["findings"][0]["reason"] == "FIREWALL_UPLOAD_NOT_PERMITTED"


def test_firewall_download_to_c_root_quarantines():
    start = start_guard_session("external_installer", corr="corr_fw_025", internet_hint=True)
    assert start["ok"] is True
    sid = start["session"]["session_id"]

    result = inspect_packets(
        app_id="external_installer",
        session_id=sid,
        expected_flow_profile="installer_update",
        packets=[
            {
                "direction": "egress",
                "protocol": "https",
                "remote_host": "repo.axion.local",
                "remote_port": 443,
                "flow_profile": "installer_update",
                "transfer_type": "download",
                "origin": "web",
                "save_path": r"C:\malware.exe",
            }
        ],
        corr="corr_fw_026",
        internet_hint=True,
    )
    assert result["ok"] is False
    assert result["code"] == "FIREWALL_PACKET_QUARANTINED"
    assert result["findings"][0]["reason"] == "PROFILE_SANDBOX_C_ROOT_BLOCKED"


def test_firewall_download_to_profile_sandbox_allowed():
    storage = ensure_profile_sandbox_storage(corr="corr_fw_027")
    assert storage["ok"] is True
    roots = [Path(x) for x in storage.get("roots", [])]
    download_root = None
    for item in roots:
        if item.name.lower() == "downloads":
            download_root = item
            break
    assert download_root is not None

    start = start_guard_session("external_installer", corr="corr_fw_028", internet_hint=True)
    assert start["ok"] is True
    sid = start["session"]["session_id"]

    result = inspect_packets(
        app_id="external_installer",
        session_id=sid,
        expected_flow_profile="installer_update",
        packets=[
            {
                "direction": "egress",
                "protocol": "https",
                "remote_host": "repo.axion.local",
                "remote_port": 443,
                "flow_profile": "installer_update",
                "transfer_type": "download",
                "origin": "web",
                "save_path": str(download_root / "safe_setup.msi"),
            }
        ],
        corr="corr_fw_029",
        internet_hint=True,
    )
    assert result["ok"] is True
    assert result["quarantined"] == 0


def test_firewall_download_blocked_by_folder_vault_domain_policy():
    original_policy = POLICY_PATH.read_text(encoding="utf-8-sig")
    try:
        policy = json.loads(original_policy)
        guard = dict(policy.get("web_download_write_guard") or {})
        guard["allowed_vault_domains"] = ["profile.vault.photos"]
        policy["web_download_write_guard"] = guard
        POLICY_PATH.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")

        storage = ensure_profile_sandbox_storage(corr="corr_fw_030")
        assert storage["ok"] is True
        roots = [Path(x) for x in storage.get("roots", [])]
        download_root = next((item for item in roots if item.name.lower() == "downloads"), None)
        assert download_root is not None

        start = start_guard_session("external_installer", corr="corr_fw_031", internet_hint=True)
        assert start["ok"] is True
        sid = start["session"]["session_id"]

        result = inspect_packets(
            app_id="external_installer",
            session_id=sid,
            expected_flow_profile="installer_update",
            packets=[
                {
                    "direction": "egress",
                    "protocol": "https",
                    "remote_host": "repo.axion.local",
                    "remote_port": 443,
                    "flow_profile": "installer_update",
                    "transfer_type": "download",
                    "origin": "web",
                    "save_path": str(download_root / "blocked_by_domain.msi"),
                }
            ],
            corr="corr_fw_032",
            internet_hint=True,
        )
        assert result["ok"] is False
        assert result["code"] == "FIREWALL_PACKET_QUARANTINED"
        assert result["findings"][0]["reason"] == "PROFILE_SANDBOX_FOLDER_DOMAIN_BLOCKED"
    finally:
        POLICY_PATH.write_text(original_policy, encoding="utf-8")


def test_firewall_unknown_ingress_adapter_quarantines():
    start = start_guard_session("external_installer", corr="corr_fw_033", internet_hint=True)
    assert start["ok"] is True
    sid = start["session"]["session_id"]

    result = inspect_packets(
        app_id="external_installer",
        session_id=sid,
        expected_flow_profile="installer_update",
        packets=[
            {
                "direction": "egress",
                "protocol": "https",
                "remote_host": "repo.axion.local",
                "remote_port": 443,
                "flow_profile": "installer_update",
                "ingress_adapter": "zigbee",
            }
        ],
        corr="corr_fw_034",
        internet_hint=True,
    )
    assert result["ok"] is False
    assert result["code"] == "FIREWALL_PACKET_QUARANTINED"
    assert result["findings"][0]["reason"] == "NETWORK_SANDBOX_ADAPTER_UNKNOWN"


def test_firewall_infection_signal_quarantines_sandbox_route():
    start = start_guard_session("external_installer", corr="corr_fw_035", internet_hint=True)
    assert start["ok"] is True
    sid = start["session"]["session_id"]
    net_sid = f"infection-test:{sid}"
    shared = share_internet_to_sandbox(
        app_id="external_installer",
        sandbox_id=net_sid,
        corr="corr_fw_035_share",
        allowed_adapters=["wired"],
        allow_upload=False,
        allow_download=True,
    )
    assert shared["ok"] is True

    result = inspect_packets(
        app_id="external_installer",
        session_id=sid,
        expected_flow_profile="installer_update",
        packets=[
            {
                "direction": "egress",
                "protocol": "https",
                "remote_host": "repo.axion.local",
                "remote_port": 443,
                "flow_profile": "installer_update",
                "network_sandbox_id": net_sid,
                "sandbox_infection_signal": True,
            }
        ],
        corr="corr_fw_036",
        internet_hint=True,
    )
    assert result["ok"] is False
    assert result["code"] == "FIREWALL_PACKET_QUARANTINED"
    assert result["findings"][0]["reason"] == "NETWORK_SANDBOX_INFECTED_QUARANTINED"
