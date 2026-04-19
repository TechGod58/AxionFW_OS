from notepad_app import save_text, snapshot


def test_notepad():
    assert save_text('demo_test', 'hello')['ok']
    assert snapshot()['count'] >= 1
