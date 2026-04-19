#!/usr/bin/env python3
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
import json, hashlib
from pathlib import Path

ROOT=Path(axion_path_str())
REG=ROOT/'config'/'actions_registry.json'
SCH=ROOT/'config'/'schema'/'actions_registry.schema.json'
OUT=ROOT/'out'/'contracts'/'actions_registry_validation.json'

try:
    import jsonschema
except Exception:
    jsonschema=None

def sha(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest().upper()

def main():
    obj=json.loads(REG.read_text(encoding='utf-8-sig'))
    sch=json.loads(SCH.read_text(encoding='utf-8-sig'))
    errs=[]
    if jsonschema is not None:
        try: jsonschema.validate(instance=obj,schema=sch)
        except Exception as e: errs.append(f'SCHEMA_FAIL:{e}')
    acts=obj.get('actions',[])
    ids=set()
    for a in acts:
        if 'category' not in a or not a.get('category'): a['category']='uncategorized'
        i=a.get('action_id')
        if i in ids: errs.append(f'DUP_ACTION_ID:{i}')
        ids.add(i)
    sorted_acts=sorted(acts,key=lambda a:(str(a.get('category','uncategorized')),str(a.get('action_id',''))))
    deterministic = acts==sorted_acts
    if not deterministic: errs.append('NON_DETERMINISTIC_ORDER')
    out={'status':'PASS' if not errs else 'FAIL','errors':errs,'deterministic_order':deterministic,'sha256':sha(REG)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(str(OUT))
    return 0 if not errs else 6

if __name__=='__main__':
    raise SystemExit(main())

