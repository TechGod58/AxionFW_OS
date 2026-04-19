from personalization_host import snapshot, set_theme, set_accent, set_wallpaper_pack, set_lock_screen_background, set_desktop_icon, set_taskbar_alignment, set_start_layout


def test_personalization_flow():
    assert set_theme('dark')['ok']
    assert set_accent('auto')['ok']
    assert set_wallpaper_pack('Axion Industries AI')['ok']
    assert set_lock_screen_background('Axion Industries AI')['ok']
    assert set_desktop_icon('recycleBin', True)['ok']
    assert set_taskbar_alignment('left')['ok']
    assert set_start_layout('windows11')['ok']
    out = snapshot('corr_personal_test_001')
    assert out['theme'] in ('light', 'dark', 'custom')
    assert 'sections' in out
