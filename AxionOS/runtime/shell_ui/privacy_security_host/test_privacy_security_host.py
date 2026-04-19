from privacy_security_host import (
    snapshot,
    set_privacy_toggle,
    set_telemetry_mode,
    set_firewall_mode,
    set_lockdown_mode,
    trigger_quick_scan,
    set_file_sharing,
    set_network_discovery,
    set_remote_desktop,
    get_os_encryption_status,
    provision_os_encryption_setup,
    rotate_os_recovery_key,
    get_firewall_guard_status,
    list_firewall_quarantine,
    adjudicate_firewall_quarantine,
    replay_firewall_quarantine,
    axion_path_str,
)
import json
from pathlib import Path


def test_privacy_security_flow():
    assert set_privacy_toggle('location', True)['ok']
    assert set_telemetry_mode('local_only')['ok']
    assert set_firewall_mode('strict')['ok']
    assert set_lockdown_mode(True)['ok']
    assert trigger_quick_scan()['ok']
    assert set_file_sharing(False)['ok']
    assert set_network_discovery(False)['ok']
    assert set_remote_desktop(True)['ok']
    assert get_os_encryption_status()['ok']
    assert get_firewall_guard_status()['ok']
    out = snapshot('corr_privsec_test_001')
    assert 'privacy' in out and 'security' in out
    assert 'sharing' in out and 'remote_desktop' in out
    assert 'os_encryption' in out
    assert 'firewall_guard' in out


def test_privacy_security_os_encryption_provision_and_rotate():
    enc_path = Path(axion_path_str("config", "OS_ENCRYPTION_STATE_V1.json"))
    before = enc_path.read_text(encoding="utf-8-sig")
    try:
        provisioned = provision_os_encryption_setup(
            computer_name="AXION-PRIVSEC",
            user_name="PrivSec User",
            user_handle="privsec_user",
            password="StrongPass123",
            pin="6789",
            enable_fingerprint=True,
            enable_face_unlock=False,
            allow_email_escrow=False,
            corr="corr_privsec_os_enc_provision_001",
        )
        assert provisioned["ok"] is True
        assert provisioned["code"] == "OS_ENCRYPTION_PROVISIONED"

        rotated = rotate_os_recovery_key(reason="privacy_security_test", corr="corr_privsec_os_enc_rotate_001")
        assert rotated["ok"] is True
        assert rotated["code"] == "OS_ENCRYPTION_RECOVERY_KEY_ROTATED"
    finally:
        enc_path.write_text(before, encoding="utf-8")


def test_privacy_security_quarantine_adjudication_and_replay():
    qdir = Path(axion_path_str("data", "quarantine", "network_packets", "external_installer", "privacy-host-test"))
    qdir.mkdir(parents=True, exist_ok=True)
    qpath = qdir / "20260417T000000000000Z_test.json"
    qpath.write_text(
        json.dumps(
            {
                "reason": "FIREWALL_REMOTE_HOST_MISMATCH",
                "session_id": "privacy-host-test",
                "app_id": "external_installer",
                "packet": {
                    "direction": "egress",
                    "protocol": "https",
                    "remote_host": "privacy-host-quarantine.example.net",
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

    listed = list_firewall_quarantine(limit=20, app_id="external_installer", corr="corr_privsec_fwq_list_001")
    assert listed["ok"] is True
    assert any(str(x.get("path")) == str(qpath) for x in listed.get("items", []))

    adjudicated = adjudicate_firewall_quarantine(
        path=str(qpath),
        decision="allow_rule",
        note="approved in host test",
        corr="corr_privsec_fwq_adjudicate_001",
    )
    assert adjudicated["ok"] is True
    assert (adjudicated.get("review") or {}).get("decision") == "allow_rule"

    replay = replay_firewall_quarantine(path=str(qpath), corr="corr_privsec_fwq_replay_001")
    assert replay["ok"] is True
    assert replay["code"] == "FIREWALL_QUARANTINE_REPLAY_OK"
