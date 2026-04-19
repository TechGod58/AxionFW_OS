from devices_host import snapshot, toggle_bluetooth, set_discoverable, pair_device, set_device_trust, set_default_audio_output, trigger_driver_rebind


def test_devices_flow():
    bt = toggle_bluetooth(True)
    assert bt['ok']
    assert bt.get('adapter_sync', {}).get('ok') is True
    assert set_discoverable(True)['ok']
    assert pair_device('bt:cc:dd', 'Travel Mouse')['ok']
    assert set_device_trust('bt:aa:bb', 'trusted')['ok']
    assert set_default_audio_output('Test Headset')['ok']
    assert trigger_driver_rebind('usb:1234:5678')['ok']
    out = snapshot('corr_devices_test_001')
    assert 'devices' in out and 'audio' in out and 'printers' in out
    assert (out.get('network_sandbox_hub') or {}).get('ok') is True
