from registry_editor_app import set_value, snapshot


def test_registry_editor():
    assert set_value('HKCU', r'Software\Axion', '1')['ok']
    s = snapshot()
    assert 'HKCU' in s
