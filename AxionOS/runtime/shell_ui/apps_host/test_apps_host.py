from pathlib import Path
import json
from apps_host import (
    snapshot,
    set_default,
    set_permission,
    request_action,
    register_program_module,
    remove_program_module,
    set_startup_enabled,
    close_app,
    one_click_connect_module,
    run_external_installer,
    MODULES_INBOX_PATH,
    MODULES_CATALOG_PATH,
    MODULES_RECEIPTS_PATH,
    build_module_provenance_envelope,
    build_installer_provenance_envelope,
    browser_experience_snapshot,
    list_browser_choices,
    get_first_boot_browser_prompt,
    choose_default_browser,
    route_browser_install_link,
)
from sandbox_projection import get_projection


def test_apps_flow():
    assert set_default('txt', 'pad')['ok']
    assert set_permission('startup', 'pad', False)['ok']
    assert set_startup_enabled('pad', True)['ok']
    assert request_action('pad', 'repair')['ok']
    out = close_app('pad')
    assert out['ok'] and out['kept_in_background'] is False
    snap = snapshot('corr_apps_test_001')
    assert 'installed' in snap and 'defaults' in snap


def test_program_module_registration():
    out = register_program_module('builder_demo', 'Builder Demo', '0.1.0')
    assert out['ok']
    snap = snapshot('corr_apps_test_002')
    assert any(app['app_id'] == 'builder_demo' and app['install_root'] == 'Program Modules' for app in snap['installed'])
    assert any(mod['app_id'] == 'builder_demo' for mod in snap['program_modules']['installed_modules'])
    cleanup = remove_program_module('builder_demo')
    assert cleanup['ok']


def test_program_module_one_click_connect():
    app_id = 'builder_click_demo'
    inbox_dir = MODULES_INBOX_PATH / app_id
    inbox_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = inbox_dir / 'module.json'
    manifest = {
        'app_id': app_id,
        'name': 'Builder Click Demo',
        'version': '0.1.0',
        'install_mode': 'copy_in_place',
        'activation_mode': 'one_click_add_to_os',
        'runtime_mode': 'capsule'
    }
    manifest['provenance'] = build_module_provenance_envelope(
        str(manifest_path),
        manifest,
        source_commit_sha='1111222233334444555566667777888899990000',
        build_pipeline_id='axion-test-modules',
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding='utf-8')

    out = one_click_connect_module(app_id, corr='corr_apps_test_click_001')
    assert out['ok']
    assert out['code'] == 'PROGRAM_MODULE_CONNECTED'
    assert out['projection']['projection_id']

    snap = snapshot('corr_apps_test_003')
    assert any(app['app_id'] == app_id for app in snap['installed'])
    assert (MODULES_CATALOG_PATH / app_id / 'module.json').exists()
    assert (MODULES_RECEIPTS_PATH / f'{app_id}.json').exists()
    assert get_projection(app_id) is not None

    cleanup = remove_program_module(app_id)
    assert cleanup['ok']


def test_run_external_installer_simulated():
    provenance = build_installer_provenance_envelope(
        'builder_legacy_setup.msi',
        family='windows',
        profile='win95',
        app_id='builder_legacy_setup',
        source_commit_sha='0000999988887777666655554444333322221111',
        build_pipeline_id='axion-test-installers',
    )
    out = run_external_installer(
        installer_path='builder_legacy_setup.msi',
        family='windows',
        profile='win95',
        app_id='builder_legacy_setup',
        corr='corr_apps_installer_test_001',
        execute=True,
        allow_live=False,
        provenance=provenance,
    )
    assert out['ok'] is True
    assert out['code'] == 'LAUNCH_INSTALLER_EXECUTED'
    assert out['installer_execution']['code'] == 'INSTALLER_EXECUTION_SIMULATED'
    assert out['installer_projection']['projection_id']


def test_module_connect_fails_closed_without_provenance():
    app_id = 'builder_click_unsigned'
    inbox_dir = MODULES_INBOX_PATH / app_id
    inbox_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = inbox_dir / 'module.json'
    manifest = {
        'app_id': app_id,
        'name': 'Unsigned Module',
        'version': '0.1.0',
        'install_mode': 'copy_in_place',
        'activation_mode': 'one_click_add_to_os',
        'runtime_mode': 'capsule',
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding='utf-8')
    out = one_click_connect_module(app_id, corr='corr_apps_unsigned_module_001')
    assert out['ok'] is False
    assert out['code'] == 'PROGRAM_MODULE_PROVENANCE_REJECTED'
    assert (out.get('provenance_check') or {}).get('code') == 'PROVENANCE_ENVELOPE_MISSING'


def test_external_installer_fails_closed_without_provenance():
    out = run_external_installer(
        installer_path='builder_unsigned_setup.msi',
        family='windows',
        profile='win95',
        app_id='builder_unsigned_setup',
        corr='corr_apps_unsigned_installer_001',
        execute=True,
        allow_live=False,
    )
    assert out['ok'] is False
    assert out['code'] == 'INSTALLER_PROVENANCE_REJECTED'
    assert (out.get('installer_provenance_check') or {}).get('code') == 'PROVENANCE_ENVELOPE_MISSING'


def test_browser_first_boot_choice_and_defaults():
    prompt = get_first_boot_browser_prompt(corr='corr_apps_browser_prompt_001')
    assert prompt['ok'] is True
    listed = list_browser_choices(corr='corr_apps_browser_choices_001')
    assert listed['ok'] is True
    assert any(item['browser_id'] == 'brave' for item in listed['choices'])
    selected = choose_default_browser('brave', corr='corr_apps_browser_choose_001')
    assert selected['ok'] is True
    assert selected['default_browser']['app_id'] == 'brave_browser'
    snap = browser_experience_snapshot(corr='corr_apps_browser_snapshot_001')
    assert snap['ok'] is True
    assert snap['first_boot']['completed'] is True


def test_browser_install_link_routed_to_installer_lane():
    out = route_browser_install_link(
        link_id='mozilla_firefox_download',
        target='https://www.mozilla.org/firefox/new/',
        installer_artifact='firefox_installer.exe',
        preferred_family='windows',
        preferred_profile='win11',
        corr='corr_apps_browser_link_001',
    )
    assert out['ok'] is True
    assert (out.get('runtime_result') or {}).get('code') == 'LAUNCH_INSTALLER_EXECUTED'


def test_productivity_and_creative_default_file_routes_present():
    snap = snapshot('corr_apps_defaults_surface_001')
    defaults = snap.get('defaults', {})
    assert defaults.get('docx') == 'write'
    assert defaults.get('xlsx') == 'sheets'
    assert defaults.get('pptx') == 'slides'
    assert defaults.get('pdf') == 'pdf_studio'
    assert defaults.get('svg') == 'vector_studio'
    assert defaults.get('psd') == 'creative_studio'
