from pathlib import Path
from video_recorder_app import record_session, snapshot


def test_video_recording():
    out = record_session('demo_webcam.json')
    assert out['ok']
    assert 'Videos' in Path(out['file']).parts
    assert snapshot()['webcam_sessions_saved_to_videos']
