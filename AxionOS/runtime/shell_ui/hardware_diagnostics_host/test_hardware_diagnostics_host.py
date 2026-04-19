from hardware_diagnostics_host import snapshot, run_test


def test_hardware_diagnostics_snapshot():
    snap = snapshot()
    assert any(item['id'] == 'memory_test_64' for item in snap['tests'])


def test_hardware_diagnostics_run():
    out = run_test('disk_integrity_scan')
    assert out['ok']
    assert out['result'] == 'PASS'
