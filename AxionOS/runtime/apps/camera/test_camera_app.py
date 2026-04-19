from pathlib import Path
from camera_app import capture_photo, snapshot


def test_camera():
    out = capture_photo('demo_camera.json')
    assert out['ok']
    assert 'Photos' in Path(out['file']).parts
    assert snapshot()['count'] >= 1
