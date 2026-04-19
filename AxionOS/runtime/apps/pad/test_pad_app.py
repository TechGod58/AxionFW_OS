from pad_app import create, save, open_doc


def test_pad_flow():
    assert create('t1', 'hello')['ok']
    assert save('t1', 'world')['ok']
    out = open_doc('t1')
    assert out['ok'] and 'world' in out['content']
