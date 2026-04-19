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
import json, os, hashlib
from datetime import datetime, timezone
from hotkey_normalize import normalize_chord

ROOT=axion_path_str()
INP=os.path.join(ROOT,'config','shell_hotkeys.json')
ACT=os.path.join(ROOT,'config','actions_registry.json')
OUT_JSON=os.path.join(ROOT,'out','ui','hotkeys_catalog.json')
OUT_MD=os.path.join(ROOT,'out','ui','hotkeys_catalog.md')
SCHEMA_VERSION='2.2'

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def sha(p):
    h=hashlib.sha256();
    with open(p,'rb') as f: h.update(f.read())
    return h.hexdigest().upper()

def main():
    obj=json.load(open(INP,'r',encoding='utf-8-sig'))
    acts=json.load(open(ACT,'r',encoding='utf-8-sig'))
    amap={a.get('action_id'):a for a in acts.get('actions',[])}
    rows=[]
    for e in obj.get('hotkeys',[]):
        aid=e.get('action_id','')
        ar=amap.get(aid,{})
        cat=e.get('category') or ar.get('category') or 'uncategorized'
        an=e.get('action_name') or ar.get('action_name') or ''
        en=bool(e.get('enabled',True)) and bool(ar.get('enabled',True) if ar else True)
        rows.append({'context':e.get('context','global'),'category':cat,'action_name':an,'action_id':aid,'enabled':en,'chord':e.get('chord',''),'normalized_chord':normalize_chord(e.get('chord','')),'notes':e.get('notes',''),'registry_present': aid in amap})
    rows.sort(key=lambda r:(r['context'], r['category'], r['normalized_chord'], r['action_id']))
    out={'timestamp_utc':now(),'schema_version':SCHEMA_VERSION,'source':INP.replace('\\','/'),'source_sha256':sha(INP),'count':len(rows),'hotkeys':rows}
    os.makedirs(os.path.dirname(OUT_JSON),exist_ok=True)
    json.dump(out,open(OUT_JSON,'w',encoding='utf-8'),indent=2)
    md=['# Hotkeys Catalog','',f"Generated: {now()}",f"Schema Version: {SCHEMA_VERSION}",f"Source SHA256: {out['source_sha256']}",'','| Context | Category | Chord | Normalized | Action | Action ID | Enabled | Registry | Notes |','|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        md.append(f"| {r['context']} | {r['category']} | {r['chord']} | {r['normalized_chord']} | {r['action_name']} | `{r['action_id']}` | {'true' if r['enabled'] else 'false'} | {'true' if r['registry_present'] else 'false'} | {r['notes']} |")
    open(OUT_MD,'w',encoding='utf-8').write('\n'.join(md)+'\n')
    print(OUT_JSON); print(OUT_MD)
    return 0
if __name__=='__main__': raise SystemExit(main())

