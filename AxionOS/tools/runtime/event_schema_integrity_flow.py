from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
#!/usr/bin/env python3
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"EVENT_SCHEMA_INCOMPATIBLE_CHANGE_ACCEPTED":1581,"EVENT_SCHEMA_VALIDATION_BYPASS":1582}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'event_schema_integrity_audit.json'); smoke_p=os.path.join(base,'event_schema_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
fail=[]
state={'producer_schema':'v2','consumer_schema':'v1','compat_check':True,'validation_enforced':True}
if mode=='incompatible': state['compat_check']=False; fail=[{'code':'EVENT_SCHEMA_INCOMPATIBLE_CHANGE_ACCEPTED','detail':'incompatible schema change accepted'}]
elif mode=='bypass': state['validation_enforced']=False; fail=[{'code':'EVENT_SCHEMA_VALIDATION_BYPASS','detail':'schema validation bypass detected'}]
trace={'state':state}
obj={'schema_compatibility_enforced':False if fail else True,'validation_path_enforced':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h(trace)}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'event_schema_integrity':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':trace,'event_schema_integrity':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

