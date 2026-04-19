from settings_host import open_category, set_search, set_pref, get_pref, snapshot


def test_category_and_search():
    assert open_category('Accessibility')['ok']
    assert set_search('theme')['ok']
    s = snapshot()
    assert s['active_category'] == 'Accessibility'
    assert s['search_query'] == 'theme'


def test_preferences():
    out = set_pref('taskbar_alignment', 'left', corr='corr_settings_001')
    assert out['ok']
    assert get_pref('taskbar_alignment')['value'] == 'left'


def test_invalid_pref():
    assert not set_pref('not_real', True)['ok']
