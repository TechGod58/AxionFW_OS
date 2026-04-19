from context_menu_host import build_menu, resolve_left_click, resolve_right_click, default_actions_for


def test_full_menu_mode():
    actions = [
        {'id': 'open', 'label': 'Open', 'advanced': False, 'enabled': True},
        {'id': 'x', 'label': 'X', 'advanced': True, 'enabled': True},
    ]
    out = build_menu(actions, target_kind='app')
    assert out['mode'] == 'full'
    assert 'primary' in out
    assert any(action['id'] == 'properties' for action in out['primary'])


def test_click_resolution():
    left = resolve_left_click('profile_folder', 'Workspace')
    right = resolve_right_click('app', 'calculator')
    assert left['action'] == 'open'
    assert right['ok']
    assert right['menu']['target_kind'] == 'app'


def test_workspace_right_click_template():
    actions = default_actions_for('workspace_surface')
    ids = [action['id'] for action in actions]
    assert 'refresh' in ids
    assert 'new_folder' in ids
    assert 'properties' in ids
    right = resolve_right_click('workspace_surface', 'Workspace')
    assert any(action['id'] == 'sort_by' for action in right['menu']['primary'])
