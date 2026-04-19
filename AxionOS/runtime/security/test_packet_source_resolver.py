import json

from packet_source_resolver import resolve_packet_sample


def test_resolve_packet_sample_prefers_explicit_packets():
    out = resolve_packet_sample(
        explicit_packets=[
            {
                "direction": "egress",
                "protocol": "https",
                "remote_host": "repo.axion.local",
                "remote_port": 443,
            }
        ],
        expected_flow_profile="installer_update",
    )
    assert out["source"] == "explicit"
    assert len(out["packets"]) == 1
    assert out["packets"][0]["flow_profile"] == "installer_update"


def test_resolve_packet_sample_reads_env_file(tmp_path, monkeypatch):
    p = tmp_path / "packets.json"
    p.write_text(
        json.dumps(
            [
                {
                    "direction": "egress",
                    "protocol": "https",
                    "remote_host": "repo.axion.local",
                    "remote_port": 443,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AXION_FIREWALL_PACKET_SOURCE", str(p))
    out = resolve_packet_sample(expected_flow_profile="installer_update")
    assert out["source"] == "env_file"
    assert out["source_path"] == str(p)
    assert len(out["packets"]) == 1
    assert out["packets"][0]["flow_profile"] == "installer_update"


def test_resolve_packet_sample_process_bound_filters_pid_and_tags_session(monkeypatch):
    class _ProcOut:
        def __init__(self, returncode=0, stdout=""):
            self.returncode = returncode
            self.stdout = stdout

    def _fake_run(cmd, capture_output, text):
        rendered = " ".join(str(x) for x in cmd)
        if "Get-NetTCPConnection" in rendered:
            return _ProcOut(
                0,
                json.dumps(
                    [
                        {
                            "LocalAddress": "10.0.0.5",
                            "LocalPort": 55001,
                            "RemoteAddress": "repo.axion.local",
                            "RemotePort": 443,
                            "OwningProcess": 111,
                            "State": "Established",
                        },
                        {
                            "LocalAddress": "10.0.0.5",
                            "LocalPort": 55002,
                            "RemoteAddress": "rogue.example.net",
                            "RemotePort": 443,
                            "OwningProcess": 222,
                            "State": "Established",
                        },
                    ]
                ),
            )
        if "Get-Process" in rendered:
            return _ProcOut(
                0,
                json.dumps(
                    [
                        {"Id": 111, "ProcessName": "python"},
                        {"Id": 222, "ProcessName": "curl"},
                    ]
                ),
            )
        return _ProcOut(1, "")

    monkeypatch.setattr("packet_source_resolver.subprocess.run", _fake_run)
    out = resolve_packet_sample(
        expected_flow_profile="installer_update",
        capture_context={
            "source": "process_bound_live",
            "app_id": "external_installer",
            "process_pid": 111,
            "process_name": "python",
            "guard_session_id": "guard-001",
            "capture_session_id": "proj-001",
        },
    )
    assert out["source"] == "process_bound_live"
    assert out["correlated"] is True
    assert len(out["packets"]) == 1
    pkt = out["packets"][0]
    assert pkt["owning_pid"] == 111
    assert pkt["process_name"] == "python"
    assert pkt["guard_session_id"] == "guard-001"
    assert pkt["capture_session_id"] == "proj-001"


def test_resolve_packet_sample_uses_linux_provider_mapping(monkeypatch):
    class _ProcOut:
        def __init__(self, returncode=0, stdout=""):
            self.returncode = returncode
            self.stdout = stdout

    def _fake_run(cmd, capture_output, text):
        rendered = " ".join(str(x) for x in cmd)
        if rendered.startswith("ss "):
            return _ProcOut(
                0,
                "\n".join(
                    [
                        "State Recv-Q Send-Q Local Address:Port Peer Address:Port Process",
                        "ESTAB 0 0 10.0.0.8:42100 repo.axion.local:443 users:((\"python\",pid=5151,fd=7))",
                        "ESTAB 0 0 10.0.0.8:42101 rogue.example.net:443 users:((\"curl\",pid=6262,fd=8))",
                    ]
                ),
            )
        return _ProcOut(1, "")

    monkeypatch.setattr("packet_source_resolver.subprocess.run", _fake_run)
    out = resolve_packet_sample(
        expected_flow_profile="installer_update",
        capture_context={
            "source": "process_bound_live",
            "runtime_family": "linux",
            "runtime_execution_model": "sandbox_linux_compat",
            "process_pid": 5151,
            "process_name": "python",
            "guard_session_id": "guard-linux-001",
        },
    )
    assert out["source"] == "process_bound_live"
    assert out["correlated"] is True
    assert out["provider_id"] == "linux_ss_snapshot_provider_v1"
    assert out["provider_kind"] == "linux_ss_snapshot"
    assert len(out["packets"]) == 1
    pkt = out["packets"][0]
    assert pkt["owning_pid"] == 5151
    assert pkt["process_name"] == "python"
    assert pkt["remote_host"] == "repo.axion.local"


def test_resolve_packet_sample_linux_provider_missing_binary_fails_soft(monkeypatch):
    def _fake_run(cmd, capture_output, text):
        raise FileNotFoundError("ss not installed")

    monkeypatch.setattr("packet_source_resolver.subprocess.run", _fake_run)
    out = resolve_packet_sample(
        expected_flow_profile="installer_update",
        capture_context={
            "source": "process_bound_live",
            "runtime_family": "linux",
            "runtime_execution_model": "sandbox_linux_compat",
            "process_pid": 5151,
            "process_name": "python",
            "guard_session_id": "guard-linux-002",
        },
    )
    assert out["source"] == "process_bound_live"
    assert out["correlated"] is True
    assert out["provider_id"] == "linux_ss_snapshot_provider_v1"
    assert out["provider_kind"] == "linux_ss_snapshot"
    assert out["packets"] == []
    assert out["note"] == "no_process_bound_connections"
