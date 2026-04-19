from command_prompt_app import snapshot, run_command


def test_snapshot_and_run():
    snap = snapshot()
    assert snap['app'] == 'Command Prompt'
    ok = run_command('dir')
    assert ok['ok'] is True
    assert ok['code'] == 'CMD_EXECUTION_OK'


def test_blocked_command():
    out = run_command('del /f test.txt')
    assert out['ok'] is False
    assert out['code'] == 'CMD_BLOCKED_COMMAND'
