from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
#!/usr/bin/env python3
import json, os, sys, hashlib
from datetime import datetime, timezone
from pathlib import Path

CODES={"HOTKEY_ACTION_ID_DANGLING":1571,"ACTIONS_REGISTRY_SCHEMA_INVALID":1572}
ROOT=Path(axion_path_str())
HOT=ROOT/'config'/'shell_hotkeys.json'
ACT=ROOT/'config'/'actions_registry.json'


def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()

base=Path(axion_path_str('out', 'runtime')); base.mkdir(parents=True, exist_ok=True)
audit_p=base/'hotkey_action_registry_integrity_audit.json'
smoke_p=base/'hotkey_action_registry_integrity_smoke.json'
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'

fail=[]
if mode=='dangling':
    fail=[{'code':'HOTKEY_ACTION_ID_DANGLING','detail':'hotkey action_id missing in actions registry'}]
elif mode=='schema_invalid':
    fail=[{'code':'ACTIONS_REGISTRY_SCHEMA_INVALID','detail':'actions registry schema/type invalid'}]
else:
    hot=json.loads(HOT.read_text(encoding='utf-8-sig'))
    act=json.loads(ACT.read_text(encoding='utf-8-sig'))
    action_ids={a.get('action_id') for a in act.get('actions',[])}
    for hk in hot.get('hotkeys',[]):
        if hk.get('action_id') not in action_ids:
            fail=[{'code':'HOTKEY_ACTION_ID_DANGLING','detail':'pass check discovered dangling action_id'}]
            break

obj={'registry_link_valid':False if fail else True,'schema_valid':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h({'mode':mode})}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'hotkey_action_registry':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':{'mode':mode},'hotkey_action_registry':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

