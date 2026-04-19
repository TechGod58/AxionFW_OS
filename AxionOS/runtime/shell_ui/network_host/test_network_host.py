from network_host import (
    snapshot,
    set_wifi,
    set_wired,
    set_airplane,
    set_vpn,
    set_computer_name,
    set_workgroup,
    set_remote_desktop,
)


def test_network_flow():
    wifi = set_wifi(True)
    assert wifi['ok']
    assert wifi.get('adapter_sync', {}).get('ok') is True
    wired = set_wired(True, 'domain')
    assert wired['ok']
    assert wired.get('adapter_sync', {}).get('ok') is True
    airplane = set_airplane(False)
    assert airplane['ok']
    assert airplane.get('adapter_sync', {}).get('wifi', {}).get('ok') is True
    vpn = set_vpn(True, 'CorpNet')
    assert vpn['ok']
    assert vpn.get('adapter_sync', {}).get('ok') is True
    assert set_computer_name('AXION-LAB')['ok']
    assert set_workgroup('AXIONWG')['ok']
    rdp = set_remote_desktop(True)
    assert rdp['ok']
    assert rdp.get('adapter_sync', {}).get('rdp_admin', {}).get('ok') is True
    out = snapshot('corr_net_test_001')
    assert out['install_identity']['computer_name'] == 'AXION-LAB'
    assert out['remote_desktop']['enabled'] is True
    assert (out.get('network_sandbox_hub') or {}).get('ok') is True
