from powershell_app import snapshot, run_command


def test_snapshot_and_run():
    snap = snapshot()
    assert snap['app'] == 'PowerShell'
    out = run_command('Get-Date')
    assert out['ok'] is True
    assert out['code'] == 'POWERSHELL_EXECUTION_OK'


def test_blocked_command():
    out = run_command('Remove-Item C:\\test -Recurse')
    assert out['ok'] is False
    assert out['code'] == 'POWERSHELL_BLOCKED_COMMAND'
