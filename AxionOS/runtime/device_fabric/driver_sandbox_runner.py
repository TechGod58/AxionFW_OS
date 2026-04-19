def sandbox_test_driver(device: dict, driver: dict):
    # v1 deterministic simulation
    if not driver.get('signed', False):
        return {"ok": False, "code": "DRV_REJECT_SIGNATURE"}

    # simple policy guard examples
    if device.get('class') in ('unknown', 'debug'):
        return {"ok": False, "code": "DRV_REJECT_POLICY"}

    return {"ok": True, "code": "DRV_SANDBOX_OK"}
