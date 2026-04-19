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
from pathlib import Path

CONTROL_PANEL_PATH = Path(axion_path_str('config', 'CONTROL_PANEL_STATE_V1.json'))
PROFILE_PATH = Path(axion_path_str('config', 'PROFILE_SHELL_FOLDERS_V1.json'))
APPS_PATH = Path(axion_path_str('config', 'APPS_STATE_V1.json'))
ICON_PATH = Path(axion_path_str('config', 'ICON_THEME_V1.json'))
PROFILE_ROOT = Path(axion_path_str('data', 'profiles', 'p1'))


def _load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def describe_target(target_type: str, target_id: str):
    icons = _load(ICON_PATH)
    if target_type == 'control_panel_item':
        state = _load(CONTROL_PANEL_PATH)
        item = next((entry for entry in state.get('allItems', []) if entry['id'] == target_id or entry['label'] == target_id), None)
        if not item:
            return {'ok': False, 'code': 'PROPERTIES_NOT_FOUND'}
        return {
            'ok': True,
            'code': 'PROPERTIES_OK',
            'target_type': target_type,
            'target_id': target_id,
            'properties': {
                'display_name': item['label'],
                'category': item.get('category'),
                'route': item.get('route'),
                'source': item.get('source'),
                'supports_properties': item.get('supportsProperties', False),
                'icon': icons.get('icons', {}).get(item.get('icon'), icons.get('defaultIcon'))
            }
        }
    if target_type == 'profile_folder':
        state = _load(PROFILE_PATH)
        wanted = str(target_id or '').strip().lower()
        folder = None
        for candidate in state.get('folders', {}).values():
            if not isinstance(candidate, dict):
                continue
            aliases = {
                str(candidate.get('displayName', '')).strip().lower(),
                str(candidate.get('pathSegment', '')).strip().lower(),
                str(candidate.get('legacyAlias', '')).strip().lower(),
                str(candidate.get('windowsBehavior', '')).strip().lower(),
            }
            for field in ('aliases', 'displayAliases', 'pathSegmentAliases'):
                values = candidate.get(field)
                if isinstance(values, list):
                    aliases.update(str(x).strip().lower() for x in values if str(x).strip())
            if wanted in aliases:
                folder = candidate
                break
        if not folder:
            return {'ok': False, 'code': 'PROPERTIES_NOT_FOUND'}
        root = PROFILE_ROOT / folder['pathSegment']
        return {
            'ok': True,
            'code': 'PROPERTIES_OK',
            'target_type': target_type,
            'target_id': target_id,
            'properties': {
                'display_name': folder['displayName'],
                'legacy_alias': folder.get('legacyAlias'),
                'root_path': str(root),
                'sandbox_kind': folder.get('sandboxKind'),
                'never_destroy_on_close': folder.get('neverDestroyOnClose'),
                'supports_left_click': folder.get('supportsLeftClick'),
                'supports_right_click': folder.get('supportsRightClick'),
                'supports_properties': folder.get('supportsProperties'),
                'icon': icons.get('folderIcons', {}).get(folder['displayName'], icons.get('defaultIcon'))
            }
        }
    if target_type == 'app':
        state = _load(APPS_PATH)
        app = next((entry for entry in state.get('installed', []) if entry['app_id'] == target_id or entry['name'] == target_id), None)
        if not app:
            return {'ok': False, 'code': 'PROPERTIES_NOT_FOUND'}
        return {
            'ok': True,
            'code': 'PROPERTIES_OK',
            'target_type': target_type,
            'target_id': target_id,
            'properties': {
                'display_name': app['name'],
                'app_id': app['app_id'],
                'version': app.get('version'),
                'runtime_mode': app.get('mode'),
                'icon': icons.get('icons', {}).get('programs', icons.get('defaultIcon'))
            }
        }
    return {'ok': False, 'code': 'PROPERTIES_UNSUPPORTED_TARGET'}


if __name__ == '__main__':
    print(json.dumps(describe_target('profile_folder', 'Workspace'), indent=2))

