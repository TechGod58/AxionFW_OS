from disk_cleanup_app import analyze, cleanup


def test_disk_cleanup():
    assert analyze()['ok']
    assert cleanup()['ok']
