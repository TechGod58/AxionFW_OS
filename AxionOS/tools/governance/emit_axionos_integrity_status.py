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
import json, os
ROOT=axion_path_str(); OUT=os.path.join(ROOT,'out','governance','AXIONOS_INTEGRITY_STATUS.md')
def load(p,d):
 try:
  with open(p,'r',encoding='utf-8-sig') as f: return json.load(f)
 except Exception: return d
cov=load(os.path.join(ROOT,'out','governance','integrity_coverage_map.json'),{'rows':[]})
inv=load(os.path.join(ROOT,'out','contracts','release_critical_gates_inventory.json'),{'gates':{}})
drift=load(os.path.join(ROOT,'out','contracts','governance_drift_check.json'),{})
health=load(os.path.join(ROOT,'out','governance','integrity_system_health.json'),{})
lines=['# AXIONOS INTEGRITY STATUS','','## integrity domain coverage',f"- contracts in map: {len(cov.get('rows',[]))}",'','## release-critical gates',f"- gates in inventory: {len(inv.get('gates',{}))}",'','## exit registry summary','- source: contracts/registry/integrity_exit_registry.json','','## governance drift result',f"- status: {drift.get('status','UNKNOWN')}",'','## system health snapshot','```json',json.dumps(health,indent=2),'```','']
os.makedirs(os.path.dirname(OUT),exist_ok=True)
open(OUT,'w',encoding='utf-8').write('\n'.join(lines))
print(OUT)

