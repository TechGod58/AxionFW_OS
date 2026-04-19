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

POLICY_PATH = axion_path_str('config', 'SHELL_CONTEXT_MENU_V1.json')


def load_policy():
    with open(POLICY_PATH, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def _catalog_action(action_id, policy):
    entry = policy.get('actionCatalog', {}).get(action_id, {})
    return {
        'id': action_id,
        'label': entry.get('label', action_id.replace('_', ' ').title()),
        'submenu': entry.get('submenu'),
        'advanced': False,
        'enabled': True
    }


def _normalize_actions(actions, policy):
    properties_id = policy.get('contextMenu', {}).get('propertiesActionId', 'properties')
    normalized = list(actions)
    if not any(action.get('id') == properties_id for action in normalized):
        normalized.append(_catalog_action(properties_id, policy))
    return normalized


def build_menu(actions, target_kind='generic'):
    p = load_policy()
    cfg = p.get('contextMenu', {})
    actions = _normalize_actions(actions, p)
    full_mode = cfg.get('mode') == 'full' and not cfg.get('showMoreOptionsEnabled', True)

    if not full_mode:
        return {'mode': 'legacy', 'primary': actions[:8], 'overflow': actions[8:], 'target_kind': target_kind}

    primary = [a for a in actions if not a.get('advanced', False)]
    advanced = [a for a in actions if a.get('advanced', False)] if cfg.get('groupAdvancedActions', True) else []

    return {
        'mode': 'full',
        'target_kind': target_kind,
        'search': bool(cfg.get('enableSearch', True)),
        'showDisabledWithReason': bool(cfg.get('showDisabledWithReason', True)),
        'primary': primary,
        'advanced': advanced,
        'all': actions if not advanced else None
    }


def resolve_left_click(target_kind: str, target_id: str):
    p = load_policy()
    target = p.get('targetPolicies', {}).get(target_kind, {})
    return {'ok': True, 'code': 'SHELL_LEFT_CLICK_RESOLVED', 'target_kind': target_kind, 'target_id': target_id, 'action': target.get('leftClick', p.get('contextMenu', {}).get('defaultLeftClick', 'open'))}


def default_actions_for(target_kind: str):
    p = load_policy()
    target = p.get('targetPolicies', {}).get(target_kind, {})
    default_ids = target.get('defaultActions', ['open', 'properties'])
    return [_catalog_action(action_id, p) for action_id in default_ids]


def resolve_right_click(target_kind: str, target_id: str, actions=None):
    p = load_policy()
    target = p.get('targetPolicies', {}).get(target_kind, {})
    if actions is None:
        actions = default_actions_for(target_kind)
    menu = build_menu(actions, target_kind=target_kind)
    return {'ok': True, 'code': 'SHELL_RIGHT_CLICK_RESOLVED', 'target_kind': target_kind, 'target_id': target_id, 'action': target.get('rightClick', p.get('contextMenu', {}).get('defaultRightClick', 'context_menu')), 'menu': menu}


if __name__ == '__main__':
    print(json.dumps(resolve_right_click('workspace_surface', 'Workspace'), indent=2))

