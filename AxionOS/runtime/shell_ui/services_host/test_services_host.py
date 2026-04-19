from services_host import snapshot, set_startup_type, start_service, stop_service


def test_services_flow():
    assert set_startup_type('svc.updates', 'auto')['ok']
    assert start_service('svc.updates')['ok']
    out = stop_service('svc.updates')
    assert out['ok']
    snap = snapshot('corr_services_test_001')
    assert 'svc.shell' in snap['services']
