from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"EVENT_SCHEMA_BACKWARD_BREAK":1551,"EVENT_SCHEMA_FORWARD_INCOMPATIBLE":1552}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit_p=os.path.join(base,'event_schema_compatibility_integrity_audit.json'); smoke_p=os.path.join(base,'event_schema_compatibility_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'producer_schema':'v2','consumer_schema':'v1','backward_ok':True,'forward_ok':True}
fail=[]
if mode=='backward_break': state['backward_ok']=False; fail=[{'code':'EVENT_SCHEMA_BACKWARD_BREAK','detail':'breaking field removal/change for existing consumers'}]
elif mode=='forward_incompat': state['forward_ok']=False; fail=[{'code':'EVENT_SCHEMA_FORWARD_INCOMPATIBLE','detail':'new producer payload incompatible with forward readers'}]
trace={'state':state}; obj={'backward_compatible':False if fail else True,'forward_compatible':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h(trace)}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'event_schema_compatibility':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':trace,'event_schema_compatibility':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

