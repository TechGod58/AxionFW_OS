from router_host import resolve


def test_route_ok():
    out = resolve('/home', 'corr_router_test_001')
    assert out['ok'] and out['host'] == 'home_host'


def test_route_control_panel():
    out = resolve('/control-panel', 'corr_router_test_003')
    assert out['ok'] and out['host'] == 'control_panel_host'


def test_route_windows_tools():
    out = resolve('/windows-tools', 'corr_router_test_003b')
    assert out['ok'] and out['host'] == 'windows_tools_host'


def test_route_management():
    out = resolve('/computer-management', 'corr_router_test_004')
    assert out['ok'] and out['host'] == 'computer_management_host'


def test_route_repair():
    out = resolve('/repair', 'corr_router_test_005')
    assert out['ok'] and out['host'] == 'repair_portal_host'


def test_route_fail():
    out = resolve('/nope', 'corr_router_test_002')
    assert not out['ok']
