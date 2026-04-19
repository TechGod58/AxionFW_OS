from driver_resolver import resolve_driver
from driver_sandbox_runner import sandbox_test_driver
from rebind_service import rebind_runtime


def test_resolve_found():
    out = resolve_driver({"bus": "usb", "vendor": "1234", "product": "5678"})
    assert out["ok"]


def test_sandbox_reject_unknown_class():
    t = sandbox_test_driver({"class": "unknown"}, {"signed": True})
    assert not t["ok"]


def test_rebind_runtime_accepts_catalog_driver():
    out = rebind_runtime({"bus": "usb", "vendor": "1234", "product": "5678"}, "drv_usb_storage_generic")
    assert out["ok"] is True
    assert out["code"] in ("RUNTIME_REBIND_OK", "RUNTIME_REBIND_NOOP_ALREADY_BOUND")


def test_rebind_runtime_rejects_unknown_driver():
    out = rebind_runtime({"bus": "usb", "vendor": "1234", "product": "5678"}, "drv_unknown")
    assert out["ok"] is False
    assert out["code"] == "RUNTIME_REBIND_DRIVER_NOT_APPROVED"
