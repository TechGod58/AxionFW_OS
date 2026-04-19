from envelope import validate_envelope


def test_envelope_missing(tmp_path):
    p = tmp_path / 'm.json'
    p.write_text('{}', encoding='utf-8')
    ok, detail = validate_envelope(str(p))
    assert not ok
    assert 'missing' in detail
