from pathlib import Path
from audio_recorder_app import record_clip, snapshot


def test_audio_recording():
    out = record_clip('demo_audio.json')
    assert out['ok']
    assert 'Music' in Path(out['file']).parts
    assert snapshot()['count'] >= 1
