from language_host import snapshot, set_display_language, add_preferred_language, remove_preferred_language, set_primary_layout, set_speech_language


def test_language_flow():
    assert set_display_language('en-US')['ok']
    assert add_preferred_language('es-ES')['ok']
    assert set_primary_layout('en-US')['ok']
    assert set_speech_language('en-US')['ok']
    out = snapshot('corr_lang_test_001')
    assert 'language' in out and 'locale' in out
    assert remove_preferred_language('es-ES')['ok']
