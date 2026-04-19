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
import argparse, json, os, hashlib
from pathlib import Path
from hotkey_normalize import normalize_chord

ROOT=Path(axion_path_str())
HOTKEYS=ROOT/'config'/'shell_hotkeys.json'
SCHEMA=ROOT/'config'/'schema'/'shell_hotkeys.schema.json'
ACTIONS=ROOT/'config'/'actions_registry.json'
OUT=ROOT/'out'/'contracts'/'shell_hotkeys_validation.json'
DRIFT=ROOT/'out'/'ui'/'hotkeys_actions_drift.json'

try:
    import jsonschema
except Exception:
    jsonschema=None

def sha(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest().upper()

def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def upgrade_if_legacy(obj):
    if isinstance(obj,dict) and 'hotkeys' in obj: return obj
    hot=[]
    for aid,cfg in (obj or {}).items():
        if not isinstance(cfg,dict): continue
        hot.append({'action_id':aid,'action_name':cfg.get('action_name',aid.replace('_',' ').title()),'context':cfg.get('context','global'),'enabled':bool(cfg.get('enabled',True)),'chord':cfg.get('chord',''), **({'notes':cfg.get('notes')} if 'notes' in cfg else {})})
    return {'schema_version':'2.0','context_allowlist':['global','editor','shell'],'hotkeys':hot}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--fix', action='store_true')
    args=ap.parse_args()

    obj=upgrade_if_legacy(load(HOTKEYS))
    actions=load(ACTIONS)
    action_ids={a.get('action_id') for a in actions.get('actions',[])}
    errs=[]

    if jsonschema is not None:
        try: jsonschema.validate(instance=obj,schema=load(SCHEMA))
        except Exception as e: errs.append(f'SCHEMA_FAIL:{e}')

    allow=set(obj.get('context_allowlist',[]))
    seen_ids=set(); seen_bind={}
    dangling=[]; duplicate=[]; invalid_chords=[]; invalid_contexts=[]

    for h in obj.get('hotkeys',[]):
        aid=h.get('action_id')
        if aid in seen_ids: errs.append(f'DUP_ACTION_ID:{aid}')
        seen_ids.add(aid)
        ctx=h.get('context','global')
        if ctx not in allow:
            errs.append(f'CONTEXT_NOT_ALLOWED:{ctx}')
            invalid_contexts.append({'action_id':aid,'context':ctx})
        try:
            nch=normalize_chord(h.get('chord',''))
            h['chord']=nch
        except Exception as e:
            errs.append(f'INVALID_CHORD:{aid}:{e}')
            invalid_chords.append({'action_id':aid,'chord':h.get('chord','')})
            continue
        if h.get('enabled',True):
            k=(ctx,nch)
            if k in seen_bind:
                errs.append(f'DUP_BINDING:{ctx}:{nch}:{seen_bind[k]}:{aid}')
                duplicate.append({'context':ctx,'chord':nch,'actions':[seen_bind[k],aid]})
            else:
                seen_bind[k]=aid
        if aid not in action_ids:
            errs.append(f'DANGLING_ACTION:{aid}')
            dangling.append({'action_id':aid,'context':ctx,'chord':h.get('chord','')})
            if args.fix:
                h['enabled']=False
                h['notes']=((h.get('notes','')+'; ').strip('; ')+ 'auto-disabled:dangling_action').strip('; ')

    obj['hotkeys']=sorted(obj.get('hotkeys',[]), key=lambda x:(x.get('context',''), x.get('chord',''), x.get('action_id','')))

    write_ok=0
    if args.fix:
        tmp=HOTKEYS.with_suffix(HOTKEYS.suffix+'.tmp')
        tmp.write_text(json.dumps(obj,indent=2),encoding='utf-8')
        json.loads(tmp.read_text(encoding='utf-8'))
        os.replace(tmp, HOTKEYS)
        write_ok=1

    # drift
    used={h.get('action_id') for h in obj.get('hotkeys',[]) if h.get('enabled',True)}
    unused=[a for a in action_ids if a not in used]
    drift={'dangling_hotkey_actions':dangling,'unused_actions':sorted(unused),'duplicate_chords':duplicate,'invalid_chords':invalid_chords,'invalid_contexts':invalid_contexts}
    DRIFT.parent.mkdir(parents=True, exist_ok=True)
    DRIFT.write_text(json.dumps(drift,indent=2),encoding='utf-8')

    res={'status':'PASS' if not errs else 'FAIL','errors':errs,'write_ok':write_ok,'sha256':sha(HOTKEYS),'json_validate_exit':0,'drift_path':str(DRIFT)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res,indent=2),encoding='utf-8')
    print(str(OUT)); print(f'WRITE_OK={write_ok}'); print(f'SHA256={res["sha256"]}'); print('JSON_VALIDATE_EXIT=0')
    return 0 if not errs else 5

if __name__=='__main__':
    raise SystemExit(main())

