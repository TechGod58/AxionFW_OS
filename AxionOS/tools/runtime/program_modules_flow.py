from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(axion_path_str())
RUNTIME_APPS_HOST = ROOT / 'runtime' / 'shell_ui' / 'apps_host'
TOOLS_RUNTIME = ROOT / 'tools' / 'runtime'
if str(RUNTIME_APPS_HOST) not in sys.path:
    sys.path.append(str(RUNTIME_APPS_HOST))
if str(TOOLS_RUNTIME) not in sys.path:
    sys.path.append(str(TOOLS_RUNTIME))

from apps_host import one_click_connect_module, snapshot, build_module_provenance_envelope
from ensure_program_layout import main as ensure_program_layout

CATALOG_PATH = ROOT / 'config' / 'PROGRAM_MODULE_CATALOG_V1.json'
MODULES_ROOT = ROOT / 'data' / 'rootfs' / 'Program Modules'
OUT_DIR = ROOT / 'out' / 'runtime'
SMOKE_PATH = OUT_DIR / 'program_modules_smoke.json'
AUDIT_PATH = OUT_DIR / 'program_modules_audit.json'


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding='utf-8')


def seed_module_manifest(app_id='builder_demo', name='Builder Demo', version='0.1.0'):
    module_dir = MODULES_ROOT / 'Inbox' / app_id
    module_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        'app_id': app_id,
        'name': name,
        'version': version,
        'source_root': 'Program Modules',
        'install_mode': 'copy_in_place',
        'activation_mode': 'one_click_add_to_os',
        'runtime_mode': 'capsule'
    }
    manifest_path = module_dir / 'module.json'
    manifest['provenance'] = build_module_provenance_envelope(
        str(manifest_path),
        manifest,
        source_commit_sha='0707070707070707070707070707070707070707',
        build_pipeline_id='axion-runtime-modules-flow',
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding='utf-8')
    return manifest, manifest_path


def main():
    ensure_program_layout()
    manifest, manifest_path = seed_module_manifest()
    result = one_click_connect_module(manifest['app_id'], corr='corr_program_modules_flow_001')
    snap = snapshot('corr_program_modules_flow_001')
    smoke = {
        'timestamp_utc': now(),
        'status': 'PASS' if result.get('ok') else 'FAIL',
        'program_modules_root': str(MODULES_ROOT),
        'manifest_path': str(manifest_path),
        'catalog_path': str(CATALOG_PATH),
        'registered_app_id': manifest['app_id'],
        'registered': result,
        'installed_modules': snap['program_modules']['installed_modules'],
        'failures': [] if result.get('ok') else [result]
    }
    audit = {
        'timestamp_utc': now(),
        'status': smoke['status'],
        'checks': ['program_roots_present', 'program_module_manifest_seeded', 'copy_in_place_registration', 'one_click_add_to_os'],
        'manifest': manifest,
        'failures': smoke['failures']
    }
    write(SMOKE_PATH, smoke)
    write(AUDIT_PATH, audit)
    if not result.get('ok'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()

