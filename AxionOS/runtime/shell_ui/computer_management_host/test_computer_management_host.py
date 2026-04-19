from computer_management_host import snapshot, open_node


def test_computer_management_snapshot():
    snap = snapshot()
    assert snap['title'] == 'Computer Management'
    assert len(snap['leftNav']) >= 3


def test_computer_management_open():
    out = open_node('disk_management')
    assert out['ok']
    assert out['group'] == 'Storage'
