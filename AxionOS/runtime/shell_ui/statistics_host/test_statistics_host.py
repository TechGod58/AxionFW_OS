from statistics_host import open_statistics, close_statistics, refresh, snapshot


def test_statistics_flow():
    assert open_statistics()['ok']
    assert refresh(processes=[{'pid': 1, 'name': 'svc.shell'}], startup_apps=['pulse_monitor'])['ok']
    s = snapshot()
    assert s['label'] == 'Statistics'
    assert len(s['processes']) == 1
    assert close_statistics()['ok']
