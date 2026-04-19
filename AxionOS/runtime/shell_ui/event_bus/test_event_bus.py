from event_bus import subscribe, publish


def test_subscribe_publish():
    subscribe('t.demo', 'x.handler')
    out = publish('t.demo', {'ok': True}, corr='corr_t1', source='test')
    assert out['ok']
    assert 'x.handler' in out['handlers']
