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
ROOT=axion_path_str()
CFG=os.path.join(ROOT,'config','release_critical_gates.json')
DOC=os.path.join(ROOT,'design','ops','CONTRACT_FIRST_DEVELOPMENT_LOOP_V1.md')

def main():
    gates=json.load(open(CFG,'r',encoding='utf-8-sig'))['gates']
    lines=open(DOC,'r',encoding='utf-8-sig').read().splitlines()
    # drop existing canonical doctrine lines for any configured gate
    ids={g['contract_id'] for g in gates}
    kept=[]
    for ln in lines:
        hit=False
        for cid in ids:
            if ln.strip()==f"- {cid} is RELEASE-CRITICAL: pipeline must fail fast unless status == PASS.":
                hit=True; break
        if not hit: kept.append(ln)
    kept.append('')
    for g in gates:
        cid=g['contract_id']
        kept.append(f"- {cid} is RELEASE-CRITICAL: pipeline must fail fast unless status == PASS.")
    with open(DOC,'w',encoding='utf-8') as f: f.write('\n'.join(kept).rstrip()+'\n')
    print(DOC)
if __name__=='__main__': main()

