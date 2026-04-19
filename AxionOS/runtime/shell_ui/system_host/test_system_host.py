from system_host import build_system_state, set_graphics_quality, set_visual_effects, set_night_light, set_power_mode, set_storage_sense


def test_system_state_and_controls():
    out = build_system_state('corr_system_test_001')
    assert 'about' in out and 'performance' in out and 'display' in out
    assert set_graphics_quality('balanced')['ok']
    assert set_visual_effects(False)['ok']
    assert set_night_light(True)['ok']
    assert set_power_mode('balanced')['ok']
    assert set_storage_sense(True)['ok']
