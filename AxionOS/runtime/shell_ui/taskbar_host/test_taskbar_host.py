from taskbar_host import apply_profile, set_alignment, pin_app, app_started, app_stopped, snapshot


def test_profile_defaults():
    apply_profile()
    s = snapshot()
    assert s['style'] == 'windows7'
    assert s['alignment'] == 'left'
    assert s['start_button']['style'] == 'orb_win7'
    assert s['superbar']['mergePinnedAndRunning'] is True


def test_alignment():
    assert set_alignment('center')['ok']
    assert not set_alignment('bad')['ok']


def test_pin_and_running():
    pin_app('axion-pad', 'Axion Pad')
    app_started('axion-pad', 'Axion Pad', 'corr_t1')
    s = snapshot()
    assert any(a['app_id'] == 'axion-pad' for a in s['pinned'])
    assert any(a['app_id'] == 'axion-pad' for a in s['running'])
    app_stopped('axion-pad')
