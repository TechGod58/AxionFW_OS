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
import json, sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit('usage: write_rail_b_plan.py <contract_id> <gate_exit>')

cid = sys.argv[1]
gx = int(sys.argv[2])
out = Path(axion_path_str('out', 'governance', 'rails', 'rail_plan.json'))
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"promotions": [{"id": cid, "gx": gx}]}, indent=2), encoding='utf-8')
print(str(out))

