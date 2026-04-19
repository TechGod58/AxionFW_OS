import json
from pathlib import Path

from app_runtime_launcher import (
    APP_ENTRYPOINTS,
    POLICY_PATH,
    resolve_compatibility,
    warm_shell_cache,
    shell_cache_entry,
    launch,
    resolve_installer_runtime,
    execute_installer_request,
    load_installer_matrix,
    build_installer_provenance_envelope,
)
from sandbox_projection import get_projection


WRAPPER_APP_IDS = [
    "access_center",
    "arcade",
    "browser_manager",
    "codex",
    "creative_studio",
    "database",
    "file_explorer",
    "gallery",
    "mail",
    "notes",
    "notepad_plus_plus",
    "pdf_studio",
    "pdf_view",
    "prompt",
    "publisher",
    "services",
    "sheets",
    "shell",
    "slides",
    "task_manager",
    "utilities",
    "vector_studio",
    "video_studio",
    "write",
]


def test_native_compatibility_and_cache():
    compat = resolve_compatibility('pad')
    assert compat['family'] == 'native_axion'
    shell = warm_shell_cache('pad')
    assert shell['reuse_ready'] is True
    assert shell_cache_entry('pad')['family'] == 'native_axion'


def test_launch_bootstraps_smart_driver_fabric(monkeypatch):
    seen = {"calls": 0}

    def _fake_bootstrap(*, corr="corr", **kwargs):
        seen["calls"] += 1
        return {
            "ok": True,
            "code": "SMART_DRIVER_FABRIC_REUSED",
            "load_once_token": "test_token",
            "corr": corr,
        }

    monkeypatch.setattr("app_runtime_launcher.ensure_smart_driver_fabric_initialized", _fake_bootstrap)
    out = launch("pad", "corr_launch_sdf_001", family="native_axion", profile="axion_default")
    assert out["ok"] is True
    assert seen["calls"] == 1


def test_windows_shell_tool_launches():
    cmd = launch('command_prompt', 'corr_cmd_launch_001')
    ps = launch('powershell', 'corr_ps_launch_001')
    run = launch('run', 'corr_run_launch_001')
    assert cmd['ok'] is True and cmd['code'] == 'LAUNCH_OK'
    assert ps['ok'] is True and ps['code'] == 'LAUNCH_OK'
    assert run['ok'] is True and run['code'] == 'LAUNCH_OK'


def test_all_declared_vm_apps_have_entrypoints_and_files():
    policy = json.loads(Path(POLICY_PATH).read_text(encoding='utf-8-sig'))
    declared = set((policy.get("apps") or {}).keys())
    mapped = set(APP_ENTRYPOINTS.keys())
    missing = sorted(declared - mapped)
    assert missing == []
    for app_id in sorted(declared):
        path = APP_ENTRYPOINTS[app_id]
        assert Path(path).exists(), f"missing entrypoint file for {app_id}: {path}"


def test_new_wrappers_launch():
    system_apps = {"codex", "file_explorer", "services", "task_manager"}
    for app_id in WRAPPER_APP_IDS:
        family = "native_system" if app_id in system_apps else "native_axion"
        profile = "system_default" if app_id in system_apps else "axion_default"
        out = launch(
            app_id,
            f"corr_wrapper_launch_{app_id}_001",
            family=family,
            profile=profile,
        )
        assert out["ok"] is True, out
        assert out["code"] == "LAUNCH_OK", out


def test_non_internet_system_program_not_sandboxed():
    out = launch('command_prompt', 'corr_system_policy_001')
    assert out['ok'] is True
    assert out['compatibility']['family'] == 'native_system'
    assert out['compatibility']['execution_model'] == 'host_native_guarded'
    assert out['system_policy']['internet_required'] is False
    assert (out.get('firewall_guard_session') or {}).get('internet_required') is False


def test_prepare_windows_environment_for_external_app():
    out = launch('legacy_winapp', 'corr_legacy_001', family='windows', profile='win95')
    assert out['ok'] is True
    assert out['code'] == 'LAUNCH_ENVIRONMENT_PREPARED'
    assert out['compatibility']['family'] == 'windows'
    assert out['compatibility']['profile'] == 'win95'


def test_prepare_linux_installer_environment():
    provenance = build_installer_provenance_envelope(
        "legacy_tool_1.0.0.deb",
        family="linux",
        profile="linux_current",
        source_commit_sha="abababababababababababababababababababab",
        build_pipeline_id="axion-test-installer",
    )
    out = launch(
        'legacy_linux_installer',
        'corr_legacy_linux_001',
        family='linux',
        profile='linux_current',
        installer='legacy_tool_1.0.0.deb',
        installer_provenance=provenance,
    )
    assert out['ok'] is True
    assert out['code'] == 'LAUNCH_ENVIRONMENT_PREPARED'
    assert out['compatibility']['family'] == 'linux'
    assert out['installer_runtime']['ok'] is True
    assert out['installer_runtime']['execution_model'].startswith('sandbox_')


def test_installer_rejects_unsupported_extension():
    info = resolve_installer_runtime('tool.unknownpkg')
    assert info['ok'] is False
    assert info['code'] == 'INSTALLER_UNSUPPORTED_EXTENSION'


def test_installer_rejects_profile_mismatch():
    info = resolve_installer_runtime('tool.msi', family='windows', profile='linux_current')
    assert info['ok'] is False
    assert info['code'] == 'INSTALLER_PROFILE_UNSUPPORTED'


def test_execute_windows_installer_simulated():
    provenance = build_installer_provenance_envelope(
        "setup_legacy.msi",
        family="windows",
        profile="win95",
        app_id="legacy_windows_installer",
        source_commit_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        build_pipeline_id="axion-test-installer",
    )
    out = launch(
        'legacy_windows_installer',
        'corr_legacy_exec_001',
        family='windows',
        profile='win95',
        installer='setup_legacy.msi',
        installer_app_id='legacy_windows_installer',
        execute_installer=True,
        installer_provenance=provenance,
    )
    assert out['ok'] is True
    assert out['code'] == 'LAUNCH_INSTALLER_EXECUTED'
    assert out['installer_execution']['code'] == 'INSTALLER_EXECUTION_SIMULATED'
    assert out['installer_replay']['signature']
    assert out['installer_projection']['projection_id']
    assert out['installer_projection_session']['runtime_layer']['mode'] == 'copy_on_write'
    assert out['installer_projection_session_close']['ok'] is True
    assert out['firewall_guard_session']['internet_required'] is True
    assert (out.get('firewall_packet_source') or {}).get('provider_id') == 'windows_tcp_snapshot_provider_v1'
    assert 'network_sandbox_share' in out
    assert get_projection('legacy_windows_installer') is not None


def test_windows_legacy_install_targets_program_files_86_runtime_image():
    provenance = build_installer_provenance_envelope(
        "sandbox_win95_setup.msi",
        family="windows",
        profile="win95",
        app_id="sandbox_win95_app",
        source_commit_sha="3131313131313131313131313131313131313131",
        build_pipeline_id="axion-test-install-root",
    )
    out = execute_installer_request(
        installer_path="sandbox_win95_setup.msi",
        corr="corr_install_root_win95_001",
        family="windows",
        profile="win95",
        app_id="sandbox_win95_app",
        allow_live_installer=False,
        provenance=provenance,
    )
    assert out["ok"] is True
    image = out.get("installer_runtime_image") or {}
    assert str(image.get("install_root", "")).endswith("Program Files (86)")
    assert str(image.get("install_path", "")).endswith("Program Files (86)\\sandbox_win95_app")
    assert Path(str(image.get("install_path", "")), "install_sandbox_manifest.json").exists()
    assert Path(str(image.get("projection_root", "")), "runtime_image_manifest.json").exists()
    assert Path(str(image.get("environment_root", "")), "runtime_environment_manifest.json").exists()
    assert (out.get("installer_runtime_context") or {}).get("install_path") == image.get("install_path")


def test_linux_install_targets_program_files_runtime_image():
    provenance = build_installer_provenance_envelope(
        "sandbox_linux_setup.deb",
        family="linux",
        profile="linux_current",
        app_id="sandbox_linux_app",
        source_commit_sha="3232323232323232323232323232323232323232",
        build_pipeline_id="axion-test-install-root",
    )
    out = execute_installer_request(
        installer_path="sandbox_linux_setup.deb",
        corr="corr_install_root_linux_001",
        family="linux",
        profile="linux_current",
        app_id="sandbox_linux_app",
        allow_live_installer=False,
        provenance=provenance,
    )
    assert out["ok"] is True
    image = out.get("installer_runtime_image") or {}
    assert str(image.get("install_root", "")).endswith("Program Files")
    assert "Program Files (86)" not in str(image.get("install_root", ""))
    assert Path(str(image.get("install_path", "")), "install_sandbox_manifest.json").exists()
    assert (out.get("installer_runtime_context") or {}).get("environment_root") == image.get("environment_root")


def test_launch_surfaces_registered_runtime_image_for_installed_app():
    provenance = build_installer_provenance_envelope(
        "runtime_image_lookup_setup.deb",
        family="linux",
        profile="linux_current",
        app_id="runtime_image_lookup_app",
        source_commit_sha="3333333333333333333333333333333333333333",
        build_pipeline_id="axion-test-runtime-image",
    )
    seeded = execute_installer_request(
        installer_path="runtime_image_lookup_setup.deb",
        corr="corr_runtime_image_seed_001",
        family="linux",
        profile="linux_current",
        app_id="runtime_image_lookup_app",
        allow_live_installer=False,
        provenance=provenance,
    )
    assert seeded["ok"] is True

    out = launch(
        "runtime_image_lookup_app",
        "corr_runtime_image_launch_001",
        family="linux",
        profile="linux_current",
    )
    assert out["ok"] is True
    assert out["code"] == "LAUNCH_ENVIRONMENT_PREPARED"
    assert (out.get("runtime_image") or {}).get("app_id") == "runtime_image_lookup_app"
    assert str((out.get("runtime_image") or {}).get("launch_mode")) == "projection_copy_on_write"


def test_installer_replay_is_deterministic_for_same_vector():
    provenance = build_installer_provenance_envelope(
        "legacy_setup.deb",
        family="linux",
        profile="linux_current",
        app_id="legacy_setup",
        source_commit_sha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        build_pipeline_id="axion-test-installer",
    )
    r1 = execute_installer_request(
        installer_path='legacy_setup.deb',
        corr='corr_replay_same_001',
        family='linux',
        profile='linux_current',
        app_id='legacy_setup',
        allow_live_installer=False,
        provenance=provenance,
    )
    r2 = execute_installer_request(
        installer_path='legacy_setup.deb',
        corr='corr_replay_same_002',
        family='linux',
        profile='linux_current',
        app_id='legacy_setup',
        allow_live_installer=False,
        provenance=provenance,
    )
    assert r1['ok'] is True and r2['ok'] is True
    assert r1['installer_replay']['signature'] == r2['installer_replay']['signature']
    assert (r1.get('firewall_packet_source') or {}).get('provider_id') == 'linux_ss_snapshot_provider_v1'


def test_installer_replay_matrix_has_deterministic_signatures():
    matrix = load_installer_matrix()
    families = matrix.get('families', {})
    for family, meta in families.items():
        ext = str(meta.get('extensions', [])[0])
        for profile in meta.get('profiles', []):
            installer_name = f"matrix_{family}_{profile}{ext}"
            first = execute_installer_request(
                installer_path=installer_name,
                corr='corr_replay_matrix_first',
                family=family,
                profile=profile,
                app_id=f"matrix_{family}_{profile}",
                allow_live_installer=False,
                provenance=build_installer_provenance_envelope(
                    installer_name,
                    family=str(family),
                    profile=str(profile),
                    app_id=f"matrix_{family}_{profile}",
                    source_commit_sha="cccccccccccccccccccccccccccccccccccccccc",
                    build_pipeline_id="axion-test-installer-matrix",
                ),
            )
            second = execute_installer_request(
                installer_path=installer_name,
                corr='corr_replay_matrix_second',
                family=family,
                profile=profile,
                app_id=f"matrix_{family}_{profile}",
                allow_live_installer=False,
                provenance=build_installer_provenance_envelope(
                    installer_name,
                    family=str(family),
                    profile=str(profile),
                    app_id=f"matrix_{family}_{profile}",
                    source_commit_sha="cccccccccccccccccccccccccccccccccccccccc",
                    build_pipeline_id="axion-test-installer-matrix",
                ),
            )
            assert first['ok'] is True and second['ok'] is True
            assert first['installer_replay']['signature'] == second['installer_replay']['signature']


def test_launch_prefers_projection_when_no_family_profile_override():
    execute_installer_request(
        installer_path='projection_ready_setup.deb',
        corr='corr_projection_seed_001',
        family='linux',
        profile='linux_2_6',
        app_id='projection_ready_app',
        allow_live_installer=False,
        provenance=build_installer_provenance_envelope(
            "projection_ready_setup.deb",
            family="linux",
            profile="linux_2_6",
            app_id="projection_ready_app",
            source_commit_sha="dddddddddddddddddddddddddddddddddddddddd",
            build_pipeline_id="axion-test-projection",
        ),
    )
    out = launch('projection_ready_app', 'corr_projection_launch_001')
    assert out['ok'] is True
    assert out['compatibility']['family'] == 'linux'
    assert out['compatibility']['profile'] == 'linux_2_6'
    assert out['projection']['projection_id']
    assert out['projection_session']['runtime_layer']['mode'] == 'copy_on_write'


def test_projection_session_reconnects_across_launches():
    execute_installer_request(
        installer_path='projection_reconnect_setup.deb',
        corr='corr_projection_seed_002',
        family='linux',
        profile='linux_current',
        app_id='projection_reconnect_app',
        allow_live_installer=False,
        provenance=build_installer_provenance_envelope(
            "projection_reconnect_setup.deb",
            family="linux",
            profile="linux_current",
            app_id="projection_reconnect_app",
            source_commit_sha="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            build_pipeline_id="axion-test-projection",
        ),
    )
    a = launch('projection_reconnect_app', 'corr_projection_launch_002')
    b = launch('projection_reconnect_app', 'corr_projection_launch_003')
    assert a['ok'] is True and b['ok'] is True
    assert a['projection_session']['session_id'] == b['projection_session']['session_id']


def test_projection_session_closed_after_runtime_process_exit(monkeypatch):
    def _fake_resolve_packet_sample(*, explicit_packets=None, expected_flow_profile=None, capture_context=None):
        pid = int((capture_context or {}).get("process_pid", 0) or 0)
        pname = str((capture_context or {}).get("process_name") or "python")
        guard_sid = str((capture_context or {}).get("guard_session_id") or "")
        capture_sid = str((capture_context or {}).get("capture_session_id") or "")
        return {
            "packets": [
                {
                    "direction": "egress",
                    "protocol": "https",
                    "remote_host": "repo.axion.local",
                    "remote_port": 443,
                    "flow_profile": expected_flow_profile or "installer_update",
                    "owning_pid": pid,
                    "process_name": pname,
                    "guard_session_id": guard_sid,
                    "capture_session_id": capture_sid,
                }
            ],
            "source": "process_bound_live",
            "correlated": True,
            "capture_session_id": capture_sid,
        }

    monkeypatch.setattr("app_runtime_launcher.resolve_packet_sample", _fake_resolve_packet_sample)
    monkeypatch.setattr(
        "firewall_guard.kernel_guard_evaluate",
        lambda app_id, packet, corr=None: {"ok": True, "code": "KERNEL_NET_GUARD_ALLOW", "effect": "allow", "rule_id": "test_allow"},
    )
    execute_installer_request(
        installer_path='projection_runtime_close_setup.deb',
        corr='corr_projection_seed_close_001',
        family='linux',
        profile='linux_current',
        app_id='notes',
        allow_live_installer=False,
        provenance=build_installer_provenance_envelope(
            "projection_runtime_close_setup.deb",
            family="linux",
            profile="linux_current",
            app_id="notes",
            source_commit_sha="ababcdababcdababcdababcdababcdababcdabcd",
            build_pipeline_id="axion-test-projection",
        ),
    )
    out = launch('notes', 'corr_projection_runtime_close_001')
    assert out['ok'] is True
    assert out['projection']['projection_id']
    assert out['projection_session']['session_id']
    assert out['projection_session_close']['ok'] is True


def test_firewall_quarantine_blocks_launch():
    provenance = build_installer_provenance_envelope(
        "blocked_setup.msi",
        family="windows",
        profile="win95",
        app_id="blocked_setup",
        source_commit_sha="ffffffffffffffffffffffffffffffffffffffff",
        build_pipeline_id="axion-test-firewall",
    )
    out = launch(
        'external_installer',
        'corr_firewall_block_001',
        family='windows',
        profile='win95',
        installer='blocked_setup.msi',
        installer_app_id='blocked_setup',
        execute_installer=True,
        installer_provenance=provenance,
        expected_flow_profile='installer_update',
        traffic_sample=[
            {
                'direction': 'egress',
                'protocol': 'https',
                'remote_host': 'rogue.example.net',
                'remote_port': 443,
                'flow_profile': 'installer_update',
            }
        ],
    )
    assert out['ok'] is False
    assert out['code'] == 'LAUNCH_FIREWALL_QUARANTINED'
    assert out['firewall_guard_inspection']['quarantined'] >= 1


def test_firewall_packet_source_env_file_used_when_no_inline_sample(tmp_path, monkeypatch):
    sample_path = tmp_path / "packets.json"
    sample_path.write_text(
        json.dumps(
            [
                {
                    "direction": "egress",
                    "protocol": "https",
                    "remote_host": "repo.axion.local",
                    "remote_port": 443,
                    "flow_profile": "installer_update",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AXION_FIREWALL_PACKET_SOURCE", str(sample_path))

    provenance = build_installer_provenance_envelope(
        "source_env_setup.msi",
        family="windows",
        profile="win95",
        app_id="source_env_setup",
        source_commit_sha="1212121212121212121212121212121212121212",
        build_pipeline_id="axion-test-firewall",
    )
    out = launch(
        'external_installer',
        'corr_firewall_source_env_001',
        family='windows',
        profile='win95',
        installer='source_env_setup.msi',
        installer_app_id='source_env_setup',
        execute_installer=True,
        installer_provenance=provenance,
        expected_flow_profile='installer_update',
    )
    assert out['ok'] is True
    assert (out.get('firewall_packet_source') or {}).get('source') == 'env_file'
    assert (out.get('firewall_guard_inspection') or {}).get('quarantined', 0) == 0


def test_installer_launch_fails_closed_without_provenance():
    out = launch(
        'external_installer',
        'corr_missing_provenance_001',
        family='windows',
        profile='win95',
        installer='unsigned_setup.msi',
        installer_app_id='unsigned_setup',
        execute_installer=True,
    )
    assert out['ok'] is False
    assert out['code'] == 'INSTALLER_PROVENANCE_REJECTED'
    assert (out.get('installer_provenance_check') or {}).get('code') == 'PROVENANCE_ENVELOPE_MISSING'


def test_installer_launch_blocks_web_save_to_c_root():
    installer_path = r"C:\unsafe_web_drop\blocked_setup.msi"
    provenance = build_installer_provenance_envelope(
        installer_path,
        family="windows",
        profile="win95",
        app_id="unsafe_web_drop",
        source_commit_sha="9191919191919191919191919191919191919191",
        build_pipeline_id="axion-test-firewall",
    )
    out = launch(
        "external_installer",
        "corr_web_save_block_001",
        family="windows",
        profile="win95",
        installer=installer_path,
        installer_app_id="unsafe_web_drop",
        execute_installer=True,
        installer_provenance=provenance,
        expected_flow_profile="installer_update",
        traffic_sample=[],
    )
    assert out["ok"] is False
    assert out["code"] == "LAUNCH_FIREWALL_QUARANTINED"
    findings = (out.get("firewall_guard_inspection") or {}).get("findings", [])
    assert findings and findings[0]["reason"] == "PROFILE_SANDBOX_C_ROOT_BLOCKED"


def test_runtime_launch_blocks_on_process_pid_correlation_mismatch(monkeypatch):
    def _fake_resolve_packet_sample(*, explicit_packets=None, expected_flow_profile=None, capture_context=None):
        capture_sid = str((capture_context or {}).get("capture_session_id") or "")
        return {
            "packets": [
                {
                    "direction": "egress",
                    "protocol": "https",
                    "remote_host": "repo.axion.local",
                    "remote_port": 443,
                    "flow_profile": expected_flow_profile or "installer_update",
                    "owning_pid": 1,
                    "process_name": "python",
                    "guard_session_id": str((capture_context or {}).get("guard_session_id") or ""),
                    "capture_session_id": capture_sid,
                }
            ],
            "source": "process_bound_live",
            "correlated": True,
            "capture_session_id": capture_sid,
        }

    monkeypatch.setattr("app_runtime_launcher.resolve_packet_sample", _fake_resolve_packet_sample)
    out = launch(
        "pad",
        "corr_runtime_pid_mismatch_001",
        family="linux",
        profile="linux_current",
        expected_flow_profile="installer_update",
    )
    assert out["ok"] is False
    assert out["code"] == "LAUNCH_FIREWALL_QUARANTINED"
    assert (out.get("firewall_guard_inspection") or {}).get("findings", [])[0]["reason"] == "FIREWALL_PID_MISMATCH"


def test_runtime_launch_allows_when_process_pid_correlation_matches(monkeypatch):
    def _fake_resolve_packet_sample(*, explicit_packets=None, expected_flow_profile=None, capture_context=None):
        pid = int((capture_context or {}).get("process_pid", 0) or 0)
        pname = str((capture_context or {}).get("process_name") or "python")
        guard_sid = str((capture_context or {}).get("guard_session_id") or "")
        capture_sid = str((capture_context or {}).get("capture_session_id") or "")
        return {
            "packets": [
                {
                    "direction": "egress",
                    "protocol": "https",
                    "remote_host": "repo.axion.local",
                    "remote_port": 443,
                    "flow_profile": expected_flow_profile or "installer_update",
                    "owning_pid": pid,
                    "process_name": pname,
                    "guard_session_id": guard_sid,
                    "capture_session_id": capture_sid,
                }
            ],
            "source": "process_bound_live",
            "correlated": True,
            "capture_session_id": capture_sid,
        }

    monkeypatch.setattr("app_runtime_launcher.resolve_packet_sample", _fake_resolve_packet_sample)
    monkeypatch.setattr(
        "firewall_guard.kernel_guard_evaluate",
        lambda app_id, packet, corr=None: {"ok": True, "code": "KERNEL_NET_GUARD_ALLOW", "effect": "allow", "rule_id": "test_allow"},
    )
    out = launch(
        "pad",
        "corr_runtime_pid_match_001",
        family="linux",
        profile="linux_current",
        expected_flow_profile="installer_update",
    )
    assert out["ok"] is True
    assert out["code"] == "LAUNCH_OK"
    assert (out.get("firewall_guard_inspection") or {}).get("quarantined", 0) == 0
    assert "network_sandbox_share" in out


def test_runtime_launch_blocks_when_correlated_stream_missing(monkeypatch):
    def _fake_resolve_packet_sample(*, explicit_packets=None, expected_flow_profile=None, capture_context=None):
        return {
            "packets": [],
            "source": "process_bound_live",
            "correlated": True,
            "note": "no_process_bound_connections",
        }

    monkeypatch.setattr("app_runtime_launcher.resolve_packet_sample", _fake_resolve_packet_sample)
    out = launch(
        "pad",
        "corr_runtime_stream_missing_001",
        family="linux",
        profile="linux_current",
        expected_flow_profile="installer_update",
    )
    assert out["ok"] is False
    assert out["code"] == "LAUNCH_FIREWALL_QUARANTINED"
    assert (out.get("firewall_guard_inspection") or {}).get("quarantined", 0) >= 1
    assert (out.get("firewall_guard_inspection") or {}).get("findings", [])[0]["reason"] == "FIREWALL_CORRELATED_STREAM_MISSING"
