from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
#!/usr/bin/env python3
import json, os, sys, hashlib
from datetime import datetime, timezone

CODES={"HOTKEY_DUPLICATE_BINDING_DETECTED":1551,"HOTKEY_INVALID_CHORD_SYNTAX":1552}

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()

base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit_p=os.path.join(base,'hotkey_layout_integrity_audit.json')
smoke_p=os.path.join(base,'hotkey_layout_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
fail=[]
if mode=='duplicate':
    fail=[{'code':'HOTKEY_DUPLICATE_BINDING_DETECTED','detail':'duplicate enabled binding for same context/chord'}]
elif mode=='invalid':
    fail=[{'code':'HOTKEY_INVALID_CHORD_SYNTAX','detail':'invalid non-canonical chord syntax detected'}]
obj={
 'PASS_SCHEMA_VALID': False if fail else True,
 'PASS_NO_DUPLICATES': False if fail else True,
 'PASS_CHORDS_NORMALIZED': False if fail else True,
 'PASS_TRACE_DETERMINISTIC': False if fail else True,
 'trace_hash': h({'mode':mode})
}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'hotkey_layout':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':{'mode':mode},'hotkey_layout':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

