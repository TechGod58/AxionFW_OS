from pulse_monitor_app import collect_snapshot


def test_collect_snapshot():
    out = collect_snapshot('corr_test_pulse_001')
    assert 'tabs' in out
    assert 'processes' in out['tabs']
