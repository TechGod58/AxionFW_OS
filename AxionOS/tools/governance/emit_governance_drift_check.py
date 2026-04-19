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
import json, os, sys
from datetime import datetime, timezone
ROOT=axion_path_str()
CFG=os.path.join(ROOT,'config','release_critical_gates.json')
GATE=os.path.join(ROOT,'ci','pipeline_contracts_gate.ps1')
DOC=os.path.join(ROOT,'design','ops','CONTRACT_FIRST_DEVELOPMENT_LOOP_V1.md')
INV=os.path.join(ROOT,'out','contracts','release_critical_gates_inventory.json')
OUT=os.path.join(ROOT,'out','contracts','governance_drift_check.json')

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

def main():
    cfg=json.load(open(CFG,'r',encoding='utf-8-sig'))['gates']
    ids=[g['contract_id'] for g in cfg]
    gate_txt=open(GATE,'r',encoding='utf-8-sig').read()
    doc_txt=open(DOC,'r',encoding='utf-8-sig').read()
    inv=json.load(open(INV,'r',encoding='utf-8-sig')) if os.path.exists(INV) else {'gates':{}}
    inv_ids=list(inv.get('gates',{}).keys())
    miss_script=[cid for cid in ids if f"@{{id='{cid}'" not in gate_txt]
    miss_doc=[cid for cid in ids if f"- {cid} is RELEASE-CRITICAL: pipeline must fail fast unless status == PASS." not in doc_txt]
    miss_inv=[cid for cid in ids if cid not in inv_ids]
    status='PASS' if not (miss_script or miss_doc or miss_inv) else 'FAIL'
    out={'timestamp_utc':now(),'status':status,'missing_in_script':miss_script,'missing_in_doctrine':miss_doc,'missing_in_inventory':miss_inv}
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    json.dump(out,open(OUT,'w',encoding='utf-8'),indent=2)
    print(OUT)
    if status!='PASS':
        print('GOVERNANCE_BASELINE_DRIFT')
        return 1
    return 0
if __name__=='__main__': raise SystemExit(main())

