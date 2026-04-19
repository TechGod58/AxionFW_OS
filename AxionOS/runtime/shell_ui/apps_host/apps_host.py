import sys
from pathlib import Path

_TOOLS_DIR = None
for _parent in Path(__file__).resolve().parents:
    if (_parent / "tools" / "common" / "pathing.py").exists():
        _TOOLS_DIR = _parent / "tools"
        break
if _TOOLS_DIR and str(_TOOLS_DIR) not in sys.path:
    sys.path.append(str(_TOOLS_DIR))

from common.pathing import axion_path


def axion_path_str(*parts):
    return str(axion_path(*parts))
import json
import sys
import shutil
from pathlib import Path
from datetime import datetime, timezone

BUS = Path(axion_path_str('runtime', 'shell_ui', 'event_bus'))
LAUNCHER_DIR = Path(axion_path_str('runtime', 'capsule', 'launchers'))
SECURITY_DIR = Path(axion_path_str('runtime', 'security'))
if str(BUS) not in sys.path:
    sys.path.append(str(BUS))
if str(LAUNCHER_DIR) not in sys.path:
    sys.path.append(str(LAUNCHER_DIR))
if str(SECURITY_DIR) not in sys.path:
    sys.path.append(str(SECURITY_DIR))

from event_bus import publish
from app_runtime_launcher import (
    launch as launch_runtime,
    resolve_compatibility,
    build_installer_provenance_envelope as build_installer_runtime_provenance_envelope,
)
from sandbox_projection import ensure_projection
from provenance_guard import verify_provenance_envelope, issue_provenance_envelope

STATE_PATH = Path(axion_path_str('config', 'APPS_STATE_V1.json'))
MODULE_CATALOG_PATH = Path(axion_path_str('config', 'PROGRAM_MODULE_CATALOG_V1.json'))
PROGRAM_LAYOUT_PATH = Path(axion_path_str('config', 'program_layout.json'))
APP_RUNTIME_PATH = Path(axion_path_str('config', 'APP_RUNTIME_BEHAVIOR_V1.json'))
FILE_TYPES_PATH = Path(axion_path_str('config', 'FILE_TYPE_CAPABILITY_MATRIX_V1.json'))
BROWSER_EXPERIENCE_PATH = Path(axion_path_str('config', 'BROWSER_EXPERIENCE_STATE_V1.json'))
MODULES_INBOX_PATH = Path(axion_path_str('data', 'rootfs', 'Program Modules', 'Inbox'))
MODULES_CATALOG_PATH = Path(axion_path_str('data', 'rootfs', 'Program Modules', 'Catalog'))
MODULES_RECEIPTS_PATH = Path(axion_path_str('data', 'rootfs', 'Program Modules', 'Receipts'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def _save(path, s):
    path.write_text(json.dumps(s, indent=2) + "\n", encoding='utf-8')


def _default_browser_experience_state():
    return {
        'version': 1,
        'policyId': 'AXION_BROWSER_EXPERIENCE_STATE_V1',
        'preinstalled': {
            'browser_id': 'brave',
            'app_id': 'brave_browser',
            'label': 'Brave Browser',
            'ready': True,
            'installed_utc': _now(),
        },
        'first_boot': {
            'requires_default_browser_choice': True,
            'prompted_utc': None,
            'completed': False,
            'completed_utc': None,
        },
        'default_browser': {
            'browser_id': 'brave',
            'app_id': 'brave_browser',
            'label': 'Brave Browser',
            'source': 'preinstalled_default',
            'changed_utc': None,
        },
        'choices': [
            {
                'browser_id': 'brave',
                'app_id': 'brave_browser',
                'label': 'Brave Browser',
                'preinstalled': True,
                'desktop_link_id': None,
                'installer_artifact': None,
            },
            {
                'browser_id': 'chrome',
                'app_id': 'browser_manager',
                'label': 'Google Chrome',
                'preinstalled': False,
                'desktop_link_id': 'google_chrome_download',
                'installer_artifact': 'chrome_installer.exe',
            },
            {
                'browser_id': 'edge',
                'app_id': 'browser_manager',
                'label': 'Microsoft Edge',
                'preinstalled': False,
                'desktop_link_id': 'microsoft_edge_download',
                'installer_artifact': 'microsoft_edge_installer.exe',
            },
            {
                'browser_id': 'firefox',
                'app_id': 'browser_manager',
                'label': 'Mozilla Firefox',
                'preinstalled': False,
                'desktop_link_id': 'mozilla_firefox_download',
                'installer_artifact': 'firefox_installer.exe',
            },
        ],
    }


def _load_browser_experience():
    if not BROWSER_EXPERIENCE_PATH.exists():
        state = _default_browser_experience_state()
        _save(BROWSER_EXPERIENCE_PATH, state)
        return state
    try:
        obj = _load(BROWSER_EXPERIENCE_PATH)
    except Exception:
        state = _default_browser_experience_state()
        _save(BROWSER_EXPERIENCE_PATH, state)
        return state
    if not isinstance(obj, dict):
        state = _default_browser_experience_state()
        _save(BROWSER_EXPERIENCE_PATH, state)
        return state
    obj.setdefault('first_boot', {})
    obj.setdefault('default_browser', {})
    obj.setdefault('preinstalled', {})
    if not isinstance(obj.get('choices'), list):
        obj['choices'] = []
    return obj


def _save_browser_experience(state):
    _save(BROWSER_EXPERIENCE_PATH, state)


def _resolve_browser_choice(state, *, browser_id: str | None = None, desktop_link_id: str | None = None):
    choices = state.get('choices', [])
    if browser_id:
        key = str(browser_id).strip().lower()
        for item in choices:
            if str(item.get('browser_id', '')).strip().lower() == key:
                return dict(item)
    if desktop_link_id:
        key = str(desktop_link_id).strip().lower()
        for item in choices:
            if str(item.get('desktop_link_id', '')).strip().lower() == key:
                return dict(item)
    return None


def _set_default_browser_file_assoc(app_id: str):
    apps = _load(STATE_PATH)
    defaults = apps.setdefault('defaults', {})
    defaults['html'] = str(app_id)
    defaults['htm'] = str(app_id)
    defaults['url'] = str(app_id)
    _save(STATE_PATH, apps)


def list_browser_choices(corr='corr_apps_browser_choices_001'):
    state = _load_browser_experience()
    default_browser = dict(state.get('default_browser', {}))
    default_id = str(default_browser.get('browser_id', '')).strip().lower()
    out = {
        'ok': True,
        'code': 'BROWSER_CHOICES_OK',
        'choices': [],
        'default_browser': default_browser,
    }
    for item in state.get('choices', []):
        row = dict(item)
        row['selected'] = str(row.get('browser_id', '')).strip().lower() == default_id
        out['choices'].append(row)
    publish('shell.apps.browser.choices', {'count': len(out['choices'])}, corr=corr, source='apps_host')
    return out


def browser_experience_snapshot(corr='corr_apps_browser_snapshot_001'):
    state = _load_browser_experience()
    publish('shell.apps.browser.snapshot', {'ok': True}, corr=corr, source='apps_host')
    return {
        'ok': True,
        'code': 'BROWSER_EXPERIENCE_SNAPSHOT_OK',
        **state,
    }


def get_first_boot_browser_prompt(corr='corr_apps_browser_firstboot_001'):
    state = _load_browser_experience()
    first_boot = state.setdefault('first_boot', {})
    choices = list_browser_choices(corr=corr)
    needs = bool(first_boot.get('requires_default_browser_choice', True)) and not bool(first_boot.get('completed', False))
    if needs and not first_boot.get('prompted_utc'):
        first_boot['prompted_utc'] = _now()
        _save_browser_experience(state)
    out = {
        'ok': True,
        'code': 'BROWSER_FIRST_BOOT_PROMPT_REQUIRED' if needs else 'BROWSER_FIRST_BOOT_PROMPT_COMPLETE',
        'required': needs,
        'first_boot': first_boot,
        'choices': choices.get('choices', []),
        'default_browser': choices.get('default_browser', {}),
    }
    publish('shell.apps.browser.first_boot.prompt', {'required': needs}, corr=corr, source='apps_host')
    return out


def choose_default_browser(browser_id: str, corr='corr_apps_browser_choose_001', complete_first_boot: bool = True):
    state = _load_browser_experience()
    choice = _resolve_browser_choice(state, browser_id=browser_id)
    if not isinstance(choice, dict):
        return {'ok': False, 'code': 'BROWSER_CHOICE_UNKNOWN', 'browser_id': browser_id}

    selected = {
        'browser_id': str(choice.get('browser_id')),
        'app_id': str(choice.get('app_id') or 'browser_manager'),
        'label': str(choice.get('label') or choice.get('browser_id')),
        'source': 'first_boot_choice' if bool(complete_first_boot) else 'settings_choice',
        'changed_utc': _now(),
    }
    state['default_browser'] = selected
    first_boot = state.setdefault('first_boot', {})
    if bool(complete_first_boot):
        first_boot['completed'] = True
        first_boot['completed_utc'] = _now()
    _save_browser_experience(state)
    _set_default_browser_file_assoc(selected['app_id'])
    publish('shell.apps.browser.default.changed', selected, corr=corr, source='apps_host')
    return {'ok': True, 'code': 'BROWSER_DEFAULT_SET_OK', 'default_browser': selected, 'first_boot': first_boot}


def route_browser_install_link(
    *,
    link_id: str,
    target: str | None = None,
    installer_artifact: str | None = None,
    preferred_family: str | None = None,
    preferred_profile: str | None = None,
    corr='corr_apps_browser_link_001',
):
    state = _load_browser_experience()
    choice = _resolve_browser_choice(state, desktop_link_id=link_id)
    browser_id = str((choice or {}).get('browser_id') or str(link_id or '').replace('_download', '').strip()).lower() or 'browser'
    artifact = str(installer_artifact or (choice or {}).get('installer_artifact') or f'{browser_id}_installer.exe').strip()
    family = str(preferred_family or 'windows').strip().lower()
    profile = str(preferred_profile or ('win11' if family == 'windows' else 'linux_current')).strip().lower()
    installer_app_id = f'{browser_id}_browser_installer'
    provenance = build_installer_provenance_envelope(
        artifact,
        family=family,
        profile=profile,
        app_id=installer_app_id,
        source_commit_sha='bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
        build_pipeline_id='axion-browser-link-router',
    )
    routed = run_external_installer(
        installer_path=artifact,
        family=family,
        profile=profile,
        app_id=installer_app_id,
        expected_flow_profile='installer_update',
        corr=corr,
        execute=True,
        allow_live=False,
        provenance=provenance,
    )
    out = {
        'ok': bool(routed.get('ok')),
        'code': 'BROWSER_INSTALL_LINK_ROUTED' if bool(routed.get('ok')) else str(routed.get('code')),
        'link_id': str(link_id),
        'target': str(target or ''),
        'browser_id': browser_id,
        'installer_artifact': artifact,
        'runtime_result': routed,
    }
    publish(
        'shell.apps.browser.install_link.routed',
        {
            'link_id': str(link_id),
            'browser_id': browser_id,
            'installer_artifact': artifact,
            'target': str(target or ''),
            'ok': bool(routed.get('ok')),
            'code': routed.get('code'),
        },
        corr=corr,
        source='apps_host',
    )
    return out


def _program_roots():
    layout = _load(PROGRAM_LAYOUT_PATH)
    return layout.get('program_layout', {})


def snapshot(corr='corr_apps_snap_001'):
    s = _load(STATE_PATH)
    browser = _load_browser_experience()
    out = {
        'ts': _now(),
        'corr': corr,
        **s,
        'program_roots': _program_roots(),
        'program_modules': _load(MODULE_CATALOG_PATH),
        'runtime_behavior': _load(APP_RUNTIME_PATH),
        'file_type_capabilities': _load(FILE_TYPES_PATH),
        'browser_experience': browser,
    }
    publish('shell.apps.refreshed', {'ok': True}, corr=corr, source='apps_host')
    return out


def set_default(ext: str, app_id: str, corr='corr_apps_default_001'):
    s = _load(STATE_PATH)
    old = s['defaults'].get(ext)
    s['defaults'][ext] = app_id
    _save(STATE_PATH, s)
    publish('shell.apps.default.changed', {'ext': ext, 'old': old, 'new': app_id}, corr=corr, source='apps_host')
    return {'ok': True, 'code': 'APPS_DEFAULT_SET_OK', 'ext': ext, 'app_id': app_id}


def set_permission(kind: str, app_id: str, enabled: bool, corr='corr_apps_perm_001'):
    s = _load(STATE_PATH)
    perms = s.get('permissions', {})
    if kind not in perms:
        return {'ok': False, 'code': 'APPS_PERMISSION_KIND_UNKNOWN'}
    if app_id not in perms[kind]:
        return {'ok': False, 'code': 'APPS_PERMISSION_APP_UNKNOWN'}
    old = perms[kind][app_id]
    perms[kind][app_id] = bool(enabled)
    _save(STATE_PATH, s)
    publish('shell.apps.permission.changed', {'kind': kind, 'app_id': app_id, 'old': old, 'new': bool(enabled)}, corr=corr, source='apps_host')
    return {'ok': True, 'code': 'APPS_PERMISSION_SET_OK'}


def set_startup_enabled(app_id: str, enabled: bool, corr='corr_apps_startup_001'):
    return set_permission('startup', app_id, enabled, corr=corr)


def close_app(app_id: str, corr='corr_apps_close_001'):
    policy = _load(APP_RUNTIME_PATH)
    close_behavior = policy.get('close_behavior', {})
    result = {
        'ok': True,
        'code': 'APP_CLOSE_TERMINATED_CAPSULE' if close_behavior.get('terminate_on_close', True) else 'APP_CLOSE_COMPLETED',
        'app_id': app_id,
        'kept_in_background': close_behavior.get('keep_running_in_background_after_close', False)
    }
    publish('shell.apps.closed', result, corr=corr, source='apps_host')
    return result


def register_program_module(app_id: str, name: str, version: str, corr='corr_program_module_001', mode='capsule'):
    apps = _load(STATE_PATH)
    catalog = _load(MODULE_CATALOG_PATH)
    if any(item.get('app_id') == app_id for item in apps.get('installed', [])):
        return {'ok': True, 'code': 'PROGRAM_MODULE_ALREADY_INSTALLED', 'app_id': app_id}

    module_entry = {
        'app_id': app_id,
        'name': name,
        'version': version,
        'root': catalog.get('roots', {}).get('program_modules', 'Program Modules'),
        'install_mode': catalog.get('onboarding', {}).get('intakeMode', 'copy_in_place'),
        'activation_mode': catalog.get('onboarding', {}).get('activationMode', 'one_click_add_to_os'),
        'runtime_mode': mode,
        'registered_utc': _now()
    }
    catalog['available_modules'] = [m for m in catalog.get('available_modules', []) if m.get('app_id') != app_id]
    catalog['installed_modules'] = [m for m in catalog.get('installed_modules', []) if m.get('app_id') != app_id]
    catalog['available_modules'].append(module_entry)
    catalog['installed_modules'].append(module_entry)
    _save(MODULE_CATALOG_PATH, catalog)

    apps.setdefault('installed', []).append({
        'app_id': app_id,
        'name': name,
        'version': version,
        'mode': mode,
        'install_root': 'Program Modules',
        'install_mode': 'copy_in_place',
        'activation_mode': 'one_click_add_to_os'
    })
    apps.setdefault('permissions', {}).setdefault('startup', {})[app_id] = False
    apps.setdefault('permissions', {}).setdefault('background', {})[app_id] = False
    _save(STATE_PATH, apps)
    publish('shell.apps.program_module.registered', module_entry, corr=corr, source='apps_host')
    return {'ok': True, 'code': 'PROGRAM_MODULE_REGISTERED', 'app_id': app_id}


def remove_program_module(app_id: str, corr='corr_program_module_remove_001'):
    apps = _load(STATE_PATH)
    catalog = _load(MODULE_CATALOG_PATH)
    before_apps = len(apps.get('installed', []))
    apps['installed'] = [item for item in apps.get('installed', []) if item.get('app_id') != app_id]
    for kind in ('startup', 'background'):
        if kind in apps.get('permissions', {}):
            apps['permissions'][kind].pop(app_id, None)
    _save(STATE_PATH, apps)

    catalog['available_modules'] = [item for item in catalog.get('available_modules', []) if item.get('app_id') != app_id]
    catalog['installed_modules'] = [item for item in catalog.get('installed_modules', []) if item.get('app_id') != app_id]
    _save(MODULE_CATALOG_PATH, catalog)

    publish('shell.apps.program_module.removed', {'app_id': app_id}, corr=corr, source='apps_host')
    return {'ok': True, 'code': 'PROGRAM_MODULE_REMOVED' if len(apps.get('installed', [])) < before_apps else 'PROGRAM_MODULE_REMOVE_NOOP', 'app_id': app_id}


def _module_provenance_metadata(manifest: dict) -> dict:
    return {
        'app_id': str(manifest.get('app_id', '')).strip(),
        'name': str(manifest.get('name', '')).strip(),
        'version': str(manifest.get('version', '')).strip(),
        'runtime_mode': str(manifest.get('runtime_mode', 'capsule')).strip(),
    }


def build_module_provenance_envelope(
    manifest_path: str,
    manifest: dict,
    *,
    source_commit_sha: str | None = None,
    build_pipeline_id: str | None = None,
    trusted_key_id: str | None = None,
) -> dict:
    issued = issue_provenance_envelope(
        subject_type='module',
        artifact_path=manifest_path,
        metadata=_module_provenance_metadata(manifest),
        source_commit_sha=source_commit_sha,
        build_pipeline_id=build_pipeline_id,
        trusted_key_id=trusted_key_id,
    )
    if not bool(issued.get('ok')):
        return {}
    envelope = issued.get('envelope')
    return dict(envelope) if isinstance(envelope, dict) else {}


def build_installer_provenance_envelope(
    installer_path: str,
    *,
    family: str | None = None,
    profile: str | None = None,
    app_id: str | None = None,
    source_commit_sha: str | None = None,
    build_pipeline_id: str | None = None,
    trusted_key_id: str | None = None,
) -> dict:
    return build_installer_runtime_provenance_envelope(
        installer_path,
        family=family,
        profile=profile,
        app_id=app_id,
        source_commit_sha=source_commit_sha,
        build_pipeline_id=build_pipeline_id,
        trusted_key_id=trusted_key_id,
    )


def one_click_connect_module_from_manifest(
    manifest_path: str,
    corr='corr_program_module_oneclick_001',
    provenance: dict | None = None,
):
    p = Path(manifest_path)
    if not p.exists() or not p.is_file():
        return {'ok': False, 'code': 'PROGRAM_MODULE_MANIFEST_MISSING', 'manifest_path': manifest_path}

    manifest = json.loads(p.read_text(encoding='utf-8-sig'))
    required = ('app_id', 'name', 'version')
    missing = [k for k in required if not manifest.get(k)]
    if missing:
        return {'ok': False, 'code': 'PROGRAM_MODULE_MANIFEST_INVALID', 'missing': missing}

    install_mode = manifest.get('install_mode', 'copy_in_place')
    activation_mode = manifest.get('activation_mode', 'one_click_add_to_os')
    if install_mode != 'copy_in_place' or activation_mode != 'one_click_add_to_os':
        return {
            'ok': False,
            'code': 'PROGRAM_MODULE_POLICY_MISMATCH',
            'install_mode': install_mode,
            'activation_mode': activation_mode
        }

    provenance_envelope = provenance if isinstance(provenance, dict) else manifest.get('provenance')
    provenance_check = verify_provenance_envelope(
        subject_type='module',
        artifact_path=str(p),
        envelope=provenance_envelope if isinstance(provenance_envelope, dict) else None,
        metadata=_module_provenance_metadata(manifest),
    )
    if not bool(provenance_check.get('ok')):
        return {
            'ok': False,
            'code': 'PROGRAM_MODULE_PROVENANCE_REJECTED',
            'manifest_path': manifest_path,
            'provenance_check': provenance_check,
        }

    app_id = manifest['app_id']
    src_dir = p.parent
    catalog_dir = MODULES_CATALOG_PATH / app_id
    receipt_path = MODULES_RECEIPTS_PATH / f"{app_id}.json"
    MODULES_CATALOG_PATH.mkdir(parents=True, exist_ok=True)
    MODULES_RECEIPTS_PATH.mkdir(parents=True, exist_ok=True)
    if catalog_dir.exists():
        shutil.rmtree(catalog_dir)
    shutil.copytree(src_dir, catalog_dir)

    mode = manifest.get('runtime_mode', 'capsule')
    reg = register_program_module(app_id, manifest['name'], manifest['version'], corr=corr, mode=mode)
    if not reg.get('ok'):
        return {'ok': False, 'code': 'PROGRAM_MODULE_REGISTER_FAILED', 'register': reg}

    runtime_family = str(manifest.get('runtime_family', 'native_axion'))
    runtime_profile = manifest.get('runtime_profile')
    compat = resolve_compatibility(app_id, family=runtime_family, profile=runtime_profile)
    projection = ensure_projection(
        app_id=app_id,
        family=str(compat.get('family', runtime_family)),
        profile=str(compat.get('profile', runtime_profile or 'axion_default')),
        execution_model=str(compat.get('execution_model', 'capsule_native')),
        source='one_click_module_connect',
        installer_path=str(p),
    )

    receipt = {
        'app_id': app_id,
        'name': manifest['name'],
        'version': manifest['version'],
        'manifest_path': str(p),
        'catalog_path': str(catalog_dir),
        'intake_mode': 'copy_in_place',
        'activation_mode': 'one_click_add_to_os',
        'projection_id': projection.get('projection_id'),
        'projection_root': projection.get('projection_root'),
        'projection_profile': projection.get('profile'),
        'provenance_subject_hash': provenance_check.get('subject_hash'),
        'provenance_key_id': provenance_check.get('trusted_key_id'),
        'provenance_pipeline_id': provenance_check.get('build_pipeline_id'),
        'provenance_check': provenance_check,
        'connected_utc': _now()
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding='utf-8')
    publish('shell.apps.program_module.one_click_connected', receipt, corr=corr, source='apps_host')
    return {
        'ok': True,
        'code': 'PROGRAM_MODULE_CONNECTED',
        'app_id': app_id,
        'catalog_path': str(catalog_dir),
        'receipt_path': str(receipt_path),
        'projection': projection,
        'provenance_check': provenance_check,
    }


def one_click_connect_module(app_id: str, corr='corr_program_module_oneclick_001', provenance: dict | None = None):
    manifest_path = MODULES_INBOX_PATH / app_id / 'module.json'
    return one_click_connect_module_from_manifest(str(manifest_path), corr=corr, provenance=provenance)


def run_external_installer(
    installer_path: str,
    family: str = None,
    profile: str = None,
    app_id: str = None,
    expected_flow_profile: str = None,
    traffic_sample: list[dict] | None = None,
    corr='corr_apps_installer_001',
    execute: bool = True,
    allow_live: bool = False,
    provenance: dict | None = None,
):
    result = launch_runtime(
        'external_installer',
        corr=corr,
        family=family,
        profile=profile,
        installer=installer_path,
        installer_app_id=app_id,
        execute_installer=bool(execute),
        allow_live_installer=bool(allow_live),
        installer_provenance=provenance,
        expected_flow_profile=expected_flow_profile,
        traffic_sample=traffic_sample,
    )
    publish(
        'shell.apps.installer.routed',
        {
            'installer_path': installer_path,
            'family': family,
            'profile': profile,
            'app_id': app_id,
            'expected_flow_profile': expected_flow_profile,
            'execute': bool(execute),
            'ok': bool(result.get('ok')),
            'code': result.get('code'),
        },
        corr=corr,
        source='apps_host',
    )
    return result


def request_action(app_id: str, action: str, corr='corr_apps_action_001'):
    if action not in ('repair', 'reset', 'uninstall', 'add_to_os'):
        return {'ok': False, 'code': 'APPS_ACTION_UNKNOWN'}
    publish('shell.apps.action.requested', {'app_id': app_id, 'action': action}, corr=corr, source='apps_host')
    return {'ok': True, 'code': 'APPS_ACTION_REQUESTED', 'app_id': app_id, 'action': action}


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))

