from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import os
import json
from pathlib import Path

CFG = Path(axion_path_str('config', 'program_layout.json'))
ROOT = Path(axion_path_str('data', 'rootfs'))


def main():
    data = json.loads(CFG.read_text(encoding="utf-8-sig"))
    layout = data["program_layout"]
    created = []
    ROOT.mkdir(parents=True, exist_ok=True)
    for key, spec in layout.items():
        p = ROOT / spec["path"]
        p.mkdir(parents=True, exist_ok=True)
        created.append(str(p))
        if key == 'program_modules':
            for child in ('Inbox', 'Catalog', 'Receipts'):
                cp = p / child
                cp.mkdir(parents=True, exist_ok=True)
                created.append(str(cp))
        if key == 'sandbox_projections':
            for child in ('Catalog', 'Environments', 'Sessions'):
                cp = p / child
                cp.mkdir(parents=True, exist_ok=True)
                created.append(str(cp))
    print(json.dumps({"status": "OK", "root": str(ROOT), "created": created}, indent=2))


if __name__ == "__main__":
    main()

