from run_dialog_app import snapshot, submit


def test_snapshot_and_aliases():
    snap = snapshot()
    assert snap['app'] == 'Run Dialog'
    assert 'cmd' in snap['known_aliases']


def test_submit_routes_known_alias():
    out = submit('cmd')
    assert out['ok'] is True
    assert out['code'] == 'RUN_DIALOG_ROUTED'
    assert out['app_id'] == 'command_prompt'


def test_submit_unknown_alias():
    out = submit('unknown_tool')
    assert out['ok'] is True
    assert out['code'] == 'RUN_DIALOG_UNKNOWN_TARGET'
