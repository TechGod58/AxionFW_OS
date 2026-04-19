from accessibility_host import snapshot, set_value


def test_accessibility_flow():
    assert set_value('vision', 'high_contrast', True)['ok']
    assert set_value('narrator', 'enabled', False)['ok']
    out = snapshot('corr_accessibility_test_001')
    assert 'sections' in out and 'narrator' in out
