import sys
from pathlib import Path

_TOOLS_DIR = None
for _parent in Path(__file__).resolve().parents:
    if (_parent / "tools" / "common" / "pathing.py").exists():
        _TOOLS_DIR = _parent / "tools"
        break
if _TOOLS_DIR and str(_TOOLS_DIR) not in sys.path:
    sys.path.append(str(_TOOLS_DIR))

from common.pathing import axion_path


def axion_path_str(*parts):
    return str(axion_path(*parts))
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

from device_watcher import detect_device
from driver_resolver import resolve_driver
from driver_sandbox_runner import sandbox_test_driver
from driver_promoter import promote
from shadow_profile_store import save_profile, load_profile
from rebind_service import rebind_runtime

AUDIT = Path(axion_path_str('data', 'audit', 'device_fabric.ndjson'))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def audit(evt):
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    evt['ts'] = evt.get('ts', now_iso())
    with AUDIT.open('a', encoding='utf-8') as f:
        f.write(json.dumps(evt) + '\n')


def device_id(device):
    return f"{device.get('bus')}:{device.get('vendor')}:{device.get('product')}"


def run_detect_flow(bus, vendor, product, cls):
    dev = detect_device(bus, vendor, product, cls)
    corr = dev['corr']
    did = device_id(dev)
    audit({"corr": corr, "event": "device.detected", "device": dev})

    shadow = load_profile(did)
    if shadow.get('ok'):
        audit({"corr": corr, "event": "driver.shadow.restore", "code": shadow['code'], "device_id": did})
        return {"corr": corr, "decision": shadow['code'], "path": "shadow_restore", "device": dev}

    r = resolve_driver(dev)
    if not r.get('ok'):
        audit({"corr": corr, "event": "driver.resolve", "code": r['code'], "device": dev})
        return {"corr": corr, "decision": "DRV_QUARANTINED", "reason": r['code'], "device": dev}

    driver = r['driver']
    audit({"corr": corr, "event": "driver.resolve", "code": r['code'], "driver": driver.get('driver_id')})

    t = sandbox_test_driver(dev, driver)
    audit({"corr": corr, "event": "driver.sandbox.test", "code": t['code']})
    if not t.get('ok'):
        return {"corr": corr, "decision": "DRV_QUARANTINED", "reason": t['code'], "device": dev}

    p = promote(dev, driver)
    audit({"corr": corr, "event": "driver.promote", "code": p['code'], "driver": driver.get('driver_id')})

    rb = rebind_runtime(dev, driver.get('driver_id'))
    audit({"corr": corr, "event": "runtime.rebind", "code": rb['code'], "driver": driver.get('driver_id')})

    save_profile(did, {
        "driver_id": driver.get('driver_id'),
        "driver_version": driver.get('version'),
        "policy_profile": "default"
    })
    audit({"corr": corr, "event": "driver.shadow.save", "code": "DRV_SHADOW_SAVE_OK", "device_id": did})

    return {"corr": corr, "decision": "DRV_OK", "driver": driver.get('driver_id'), "device": dev}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    d = sub.add_parser('detect')
    d.add_argument('--bus', required=True)
    d.add_argument('--vendor', required=True)
    d.add_argument('--product', required=True)
    d.add_argument('--class', dest='cls', default='unknown')

    args = ap.parse_args()

    if args.cmd == 'detect':
        out = run_detect_flow(args.bus, args.vendor, args.product, args.cls)
        print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()

