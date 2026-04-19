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
from pathlib import Path

CATALOG_PATH = Path(axion_path_str('config', 'DEVICE_DRIVER_CATALOG_V1.json'))


def ensure_catalog():
    if not CATALOG_PATH.exists():
        CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        seed = {
            "version": 1,
            "drivers": [
                {
                    "match": {"bus": "usb", "vendor": "1234", "product": "5678"},
                    "driver_id": "drv_usb_storage_generic",
                    "version": "1.0.0",
                    "signed": True
                },
                {
                    "match": {"bus": "pci", "vendor": "8086", "product": "100e"},
                    "driver_id": "drv_pci_net_e1000",
                    "version": "1.0.0",
                    "signed": True
                }
            ]
        }
        CATALOG_PATH.write_text(json.dumps(seed, indent=2), encoding='utf-8')


def load_catalog():
    ensure_catalog()
    return json.loads(CATALOG_PATH.read_text(encoding='utf-8-sig'))


def resolve_driver(device: dict):
    catalog = load_catalog()
    for d in catalog.get('drivers', []):
        m = d.get('match', {})
        if all(str(device.get(k, '')).lower() == str(v).lower() for k, v in m.items()):
            return {"ok": True, "code": "DRV_RESOLVE_OK", "driver": d}
    return {"ok": False, "code": "DRV_RESOLVE_NOT_FOUND"}

