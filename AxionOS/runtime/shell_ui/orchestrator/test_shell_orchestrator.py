import sys
from pathlib import Path

from shell_orchestrator import run_demo, handle_hotkey, dispatch_shell_action

APPS_HOST_DIR = Path(__file__).resolve().parents[1] / "apps_host"
if str(APPS_HOST_DIR) not in sys.path:
    sys.path.append(str(APPS_HOST_DIR))

from apps_host import build_installer_provenance_envelope


def test_orchestrator_demo():
    out = run_demo('corr_test_orch_001')
    assert out['taskbar']['alignment'] == 'left'
    assert out['start']['is_open'] is True


def test_boss_button_toggle_restore_and_suppress():
    probe = handle_hotkey('z', ctrl=True, alt=False, shift=False, focus_context='non-input', current_view='/workbench', ui_state={'tab': 'contracts'}, corr='corr_boss_001_probe')
    on = probe
    if probe.get('code') == 'BOSS_BUTTON_OFF':
        on = handle_hotkey('z', ctrl=True, alt=False, shift=False, focus_context='non-input', current_view='/workbench', ui_state={'tab': 'contracts'}, corr='corr_boss_001')
    assert on['ok'] and on['code'] == 'BOSS_BUTTON_ON'
    assert on['view'] == 'status_dashboard'

    off = handle_hotkey('z', ctrl=True, alt=False, shift=False, focus_context='non-input', current_view='status_dashboard', corr='corr_boss_002')
    assert off['ok'] and off['code'] == 'BOSS_BUTTON_OFF'
    assert off['view'] == '/workbench'

    sup = handle_hotkey('z', ctrl=True, alt=False, shift=False, focus_context='input', current_view='/editor', corr='corr_boss_003')
    assert sup['ok'] and sup['code'] == 'BOSS_BUTTON_SUPPRESSED_INPUT_FOCUS'


def test_dispatch_shell_action_control_panel_installer():
    provenance = build_installer_provenance_envelope(
        'orch_setup_legacy.msi',
        family='windows',
        profile='win95',
        source_commit_sha='0606060606060606060606060606060606060606',
        build_pipeline_id='axion-test-orchestrator',
    )
    out = dispatch_shell_action(
        'control_panel',
        'run_installer',
        {
            'item': 'Programs and Features',
            'args': {
                'installer_path': 'orch_setup_legacy.msi',
                'family': 'windows',
                'profile': 'win95',
                'execute': True,
                'provenance': provenance,
            },
        },
        corr='corr_orch_dispatch_001',
    )
    assert out['ok'] is True
    assert out['code'] == 'ORCH_ACTION_DISPATCHED'
    assert out['result']['result']['result']['code'] == 'LAUNCH_INSTALLER_EXECUTED'
