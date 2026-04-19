from home_host import build_home, quick_toggle


def test_home_build_and_toggle():
    out = build_home("corr_home_test_001")
    assert "quick_toggles" in out
    assert "location" in out["quick_toggles"]

    t = quick_toggle("wifi", False, "corr_home_test_002")
    assert t["ok"]

    loc = quick_toggle("location", True, "corr_home_test_003")
    assert loc["ok"]

    out2 = build_home("corr_home_test_004")
    assert out2["quick_toggles"]["location"] is True
