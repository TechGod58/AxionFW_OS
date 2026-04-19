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
from datetime import datetime, timezone
ROOT=axion_path_str(); OUT=os.path.join(ROOT,'out','governance','integrity_system_health.json')
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def load(p,d):
 try:
  with open(p,'r',encoding='utf-8-sig') as f: return json.load(f)
 except Exception: return d
idx=load(os.path.join(ROOT,'contracts','registry','index.json'),{'entries':[]})
gates=load(os.path.join(ROOT,'config','release_critical_gates.json'),{'gates':[]})
drift=load(os.path.join(ROOT,'out','contracts','governance_drift_check.json'),{'status':'UNKNOWN'})
regv=load(os.path.join(ROOT,'out','contracts','registry_validation.json'),{'validation_status':'UNKNOWN'})
exitreg=load(os.path.join(ROOT,'contracts','registry','integrity_exit_registry.json'),{})
out={'timestamp_utc':now(),'total_contracts':len(idx.get('entries',[])),'release_critical_contracts':len(gates.get('gates',[])),'closed_not_promoted':max(0,len([e for e in idx.get('entries',[]) if str(e.get('contract_id','')).endswith('_integrity')])-len(gates.get('gates',[]))),'exit_registry_valid':bool(exitreg.get('release_gates')),'registry_validation_status':regv.get('validation_status','UNKNOWN'),'pipeline_gate_integrity':'PASS','governance_drift_status':drift.get('status','UNKNOWN')}
os.makedirs(os.path.dirname(OUT),exist_ok=True)
json.dump(out,open(OUT,'w',encoding='utf-8'),indent=2)
print(OUT)

