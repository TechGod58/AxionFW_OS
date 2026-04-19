from clock_app import add_alarm, add_timer, snapshot


def test_clock_adds():
    assert add_alarm('Morning', '2026-03-02T07:00:00-05:00')['ok']
    assert add_timer('Tea', 60)['ok']
    s = snapshot()
    assert len(s['alarms']) >= 1
