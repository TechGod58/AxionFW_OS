from media_codecs_app import snapshot


def test_media_codecs_snapshot():
    snap = snapshot()
    assert snap['policyId'] == 'AXION_MEDIA_CODECS_V1'
    assert snap['captureDefaults']['webcamSessionsSavedToVideos']
