from calendar_app import add_event, list_events


def test_calendar_add_event():
    assert add_event('Build Sync', '2026-03-02T10:00:00-05:00', '2026-03-02T10:30:00-05:00', 10)['ok']
    ev = list_events()
    assert len(ev) >= 1
