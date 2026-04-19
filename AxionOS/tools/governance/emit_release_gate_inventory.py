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
import argparse, glob, json, os
from datetime import datetime, timezone
ROOT=axion_path_str()
CFG=os.path.join(ROOT,'config','release_critical_gates.json')
GATE=os.path.join(ROOT,'ci','pipeline_contracts_gate.ps1')
DOC=os.path.join(ROOT,'design','ops','CONTRACT_FIRST_DEVELOPMENT_LOOP_V1.md')
DEFAULT_OUT=os.path.join(ROOT,'out','contracts','release_critical_gates_inventory.json')

def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

def load(p):
    with open(p,'r',encoding='utf-8-sig') as f:
        return json.load(f)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out', default=DEFAULT_OUT)
    args=ap.parse_args()

    cfg=load(CFG)
    gates=cfg.get('gates',[])
    gate_text=open(GATE,'r',encoding='utf-8-sig').read()
    doc_text=open(DOC,'r',encoding='utf-8-sig').read()
    reports=sorted(glob.glob(os.path.join(ROOT,'out','contracts','*GATE_POLICY_PASS_PROOF.json')), key=os.path.getmtime, reverse=True)

    out={'inventory_timestamp_utc':now(),'source':'config/release_critical_gates.json','gates':{}}
    for g in gates:
        cid=g['contract_id']
        rec={
            'gate_exit':g['gate_exit'],
            'category':g.get('category'),
            'script_present':f"@{{id='{cid}'" in gate_text,
            'doctrine_present':f"- {cid} is RELEASE-CRITICAL: pipeline must fail fast unless status == PASS." in doc_text,
            'last_pass_proof_report_path':None
        }
        for rp in reports:
            try:
                obj=load(rp)
                sec=obj.get(cid)
                if isinstance(sec,dict) and sec.get('status')=='PASS':
                    rec['last_pass_proof_report_path']=rp
                    break
            except Exception:
                pass
        out['gates'][cid]=rec

    os.makedirs(os.path.dirname(args.out),exist_ok=True)
    with open(args.out,'w',encoding='utf-8') as f:
        json.dump(out,f,indent=2)
        f.write('\n')
    print(args.out)

if __name__=='__main__':
    main()

