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
DOC=os.path.join(ROOT,'design','ops','CONTRACT_FIRST_DEVELOPMENT_LOOP_V1.md')
CONTRACTS=os.path.join(ROOT,'contracts','registry','index.json')

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def load(p):
    with open(p,'r',encoding='utf-8-sig') as f: return json.load(f)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out-json',default=os.path.join(ROOT,'out','governance','integrity_coverage_map.json'))
    ap.add_argument('--out-md',default=os.path.join(ROOT,'out','governance','integrity_coverage_map.md'))
    args=ap.parse_args()
    gates=load(CFG)['gates']; idx=load(CONTRACTS); doc=open(DOC,'r',encoding='utf-8-sig').read()
    by_id={e['contract_id']:e for e in idx.get('entries',[])}
    reports=sorted(glob.glob(os.path.join(ROOT,'out','contracts','*PASS*.json')), key=os.path.getmtime, reverse=True)
    rows=[]
    for g in gates:
        cid=g['contract_id']; last=None
        for rp in reports:
            try:
                obj=load(rp); sec=obj.get(cid)
                if isinstance(sec,dict) and sec.get('status')=='PASS': last=rp; break
            except Exception: pass
        rows.append({'contract_id':cid,'risk_class':'integrity_control','slice_negative_exits':[],'gate_exit':g['gate_exit'],'release_critical':True,'category':g.get('category'),'doctrine_present':f"- {cid} is RELEASE-CRITICAL: pipeline must fail fast unless status == PASS." in doc,'last_pass_report':last,'registry_path':by_id.get(cid,{}).get('path')})
    out={'timestamp_utc':now(),'count':len(rows),'rows':rows}
    os.makedirs(os.path.dirname(args.out_json),exist_ok=True)
    with open(args.out_json,'w',encoding='utf-8') as f: json.dump(out,f,indent=2); f.write('\n')
    md=['# Integrity Coverage Map','',f"Generated: {out['timestamp_utc']}",'','| contract_id | category | gate_exit | release_critical | doctrine_present | last_pass_report |','|---|---:|---:|---:|---:|---|']
    for r in rows: md.append(f"| {r['contract_id']} | {r['category']} | {r['gate_exit']} | {r['release_critical']} | {r['doctrine_present']} | {r['last_pass_report'] or ''} |")
    with open(args.out_md,'w',encoding='utf-8') as f: f.write('\n'.join(md)+'\n')
    print(args.out_json); print(args.out_md)
if __name__=='__main__': main()

