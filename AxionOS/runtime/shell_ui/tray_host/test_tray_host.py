from tray_host import apply_runtime_policy, set_toggle, update_sound, push_notification, snapshot, sync_running_apps


def test_toggle_and_sound():
    assert apply_runtime_policy()['ok']
    assert set_toggle('wifi', True)['ok']
    out = update_sound(level=12, muted=False)
    assert out['ok']


def test_notifications():
    push_notification('Axion', 'Test', 'info', 'corr_tn_1')
    s = snapshot()
    assert len(s['notifications']) >= 1


def test_running_apps_sync():
    sync_running_apps([{'app_id': 'pad', 'label': 'Axion Pad'}])
    s = snapshot()
    assert len(s['running_apps']) == 1
    assert s['app_runtime_policy']['keep_running_in_background_after_close'] is False
