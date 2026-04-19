from repair_portal_host import snapshot, open_surface


def test_repair_portal_snapshot():
    snap = snapshot()
    assert any(item['id'] == 'firmware_repair' for item in snap['surfaces'])


def test_repair_portal_surface():
    out = open_surface('hardware_diagnostics')
    assert out['ok']
