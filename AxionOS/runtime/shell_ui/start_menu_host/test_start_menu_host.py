import json
import sys
from pathlib import Path

from start_menu_host import (
    apply_profile,
    open_menu,
    close_menu,
    set_query,
    pin_app,
    add_recent_program,
    invoke_power,
    invoke_quick_action,
    snapshot,
    axion_path_str,
)

APPS_HOST_DIR = Path(__file__).resolve().parents[1] / "apps_host"
if str(APPS_HOST_DIR) not in sys.path:
    sys.path.append(str(APPS_HOST_DIR))

from apps_host import build_module_provenance_envelope, build_installer_provenance_envelope


def test_profile_defaults():
    apply_profile()
    s = snapshot()
    assert s['style'] == 'windows7_classic'
    assert s['search_box_position'] == 'bottom'
    assert any(link['displayName'] == 'Workspace' for link in s['right_column_links'])
    assert any(link['displayName'] == 'Connections' for link in s['right_column_links'])
    assert any(q['id'] == 'quick_connect_module' for q in s['quick_actions'])
    assert any(q['id'] == 'quick_review_firewall_quarantine' for q in s['quick_actions'])
    assert any(q['id'] == 'quick_launch_command_prompt' for q in s['quick_actions'])
    assert any(q['id'] == 'quick_launch_powershell' for q in s['quick_actions'])
    assert any(q['id'] == 'quick_launch_run_dialog' for q in s['quick_actions'])
    assert any(q['id'] == 'quick_pending_bios_settings' for q in s['quick_actions'])


def test_open_close():
    assert open_menu()['ok']
    assert snapshot()['is_open'] is True
    assert close_menu()['ok']


def test_pin_and_query():
    pin_app('axion-pad', 'Axion Pad')
    set_query('pad')
    s = snapshot()
    assert any(a['app_id'] == 'axion-pad' for a in s['pinned'])
    assert s['query'] == 'pad'


def test_recent_and_power():
    add_recent_program('axion-calc', 'Axion Calculator')
    out = invoke_power('restart')
    assert out['ok']


def test_quick_action_installer_dispatch():
    apply_profile()
    provenance = build_installer_provenance_envelope(
        'start_menu_setup.msi',
        family='windows',
        profile='win95',
        app_id='start_menu_setup',
        source_commit_sha='0303030303030303030303030303030303030303',
        build_pipeline_id='axion-test-startmenu',
    )
    out = invoke_quick_action(
        'quick_run_windows_installer',
        {
            'installer_path': 'start_menu_setup.msi',
            'profile': 'win95',
            'app_id': 'start_menu_setup',
            'provenance': provenance,
        },
        corr='corr_startmenu_quick_installer_001',
    )
    assert out['ok'] is True
    assert out['dispatch']['result']['result']['code'] == 'LAUNCH_INSTALLER_EXECUTED'


def test_quick_action_module_connect_dispatch():
    apply_profile()
    app_id = 'startmenu_click_demo'
    inbox = Path(axion_path_str('data', 'rootfs', 'Program Modules', 'Inbox', app_id))
    inbox.mkdir(parents=True, exist_ok=True)
    manifest_path = inbox / 'module.json'
    manifest = {
        'app_id': app_id,
        'name': 'StartMenu Click Demo',
        'version': '0.1.0',
        'install_mode': 'copy_in_place',
        'activation_mode': 'one_click_add_to_os',
        'runtime_mode': 'capsule',
    }
    manifest['provenance'] = build_module_provenance_envelope(
        str(manifest_path),
        manifest,
        source_commit_sha='0404040404040404040404040404040404040404',
        build_pipeline_id='axion-test-startmenu',
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

    out = invoke_quick_action(
        'quick_connect_module',
        {'app_id': app_id},
        corr='corr_startmenu_quick_connect_001',
    )
    assert out['ok'] is True
    assert out['dispatch']['result']['result']['code'] == 'PROGRAM_MODULE_CONNECTED'


def test_quick_action_firewall_quarantine_review_dispatch():
    apply_profile()
    qdir = Path(axion_path_str('data', 'quarantine', 'network_packets', 'external_installer', 'startmenu-test'))
    qdir.mkdir(parents=True, exist_ok=True)
    (qdir / '20260417T000000000002Z_test.json').write_text(
        json.dumps(
            {
                'reason': 'FIREWALL_REMOTE_HOST_MISMATCH',
                'session_id': 'startmenu-test',
                'app_id': 'external_installer',
                'packet': {
                    'direction': 'egress',
                    'protocol': 'https',
                    'remote_host': 'startmenu-quarantine.example.net',
                    'remote_port': 443,
                    'flow_profile': 'installer_update',
                },
                'quarantined_utc': '2026-04-17T00:00:00Z',
            },
            indent=2,
        ) + '\n',
        encoding='utf-8',
    )

    out = invoke_quick_action(
        'quick_review_firewall_quarantine',
        {'app_id': 'external_installer', 'limit': 5},
        corr='corr_startmenu_quick_fwq_001',
    )
    assert out['ok'] is True
    assert out['dispatch']['result']['result']['code'] == 'FIREWALL_QUARANTINE_LIST_OK'


def test_quick_action_windows_shell_tools_launch():
    apply_profile()
    cmd = invoke_quick_action('quick_launch_command_prompt', {}, corr='corr_startmenu_quick_cmd_001')
    ps = invoke_quick_action('quick_launch_powershell', {}, corr='corr_startmenu_quick_ps_001')
    run = invoke_quick_action('quick_launch_run_dialog', {}, corr='corr_startmenu_quick_run_001')
    assert cmd['ok'] is True
    assert ps['ok'] is True
    assert run['ok'] is True
    assert cmd['dispatch']['result']['code'] == 'WINDOWS_TOOLS_LAUNCH_OK'
    assert ps['dispatch']['result']['code'] == 'WINDOWS_TOOLS_LAUNCH_OK'
    assert run['dispatch']['result']['code'] == 'WINDOWS_TOOLS_LAUNCH_OK'


def test_quick_action_pending_bios_settings_dispatch():
    apply_profile()
    out = invoke_quick_action('quick_pending_bios_settings', {}, corr='corr_startmenu_quick_bios_001')
    assert out['ok'] is True
    assert out['dispatch']['result']['code'] == 'WINDOWS_TOOLS_ACTION_OK'
    assert out['dispatch']['result']['result']['code'] in ('BIOS_SETTINGS_PENDING_FOUND', 'BIOS_SETTINGS_NONE_PENDING')
