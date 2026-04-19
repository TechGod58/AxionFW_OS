from advanced_system_host import snapshot, open_tab


def test_advanced_system_snapshot():
    snap = snapshot()
    assert snap['title'] == 'Advanced System'
    assert len(snap['tabs']) >= 5


def test_advanced_system_open():
    out = open_tab('startup_recovery')
    assert out['ok']
    assert out['label'] == 'Startup and Recovery'
