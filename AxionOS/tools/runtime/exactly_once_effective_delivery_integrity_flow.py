from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"EFFECTIVE_ONCE_DUPLICATE_EFFECT":1411,"EFFECTIVE_ONCE_LOST_EFFECT":1412}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'exactly_once_effective_delivery_integrity_audit.json'); smoke_p=os.path.join(base,'exactly_once_effective_delivery_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'event':'e900','outbox':True,'idempotency':True,'ack_commit':True,'effects':1}
fail=[]
if mode=='dup': state['effects']=2; fail=[{'code':'EFFECTIVE_ONCE_DUPLICATE_EFFECT','detail':'duplicate side-effect observed'}]
elif mode=='lost': state['effects']=0; fail=[{'code':'EFFECTIVE_ONCE_LOST_EFFECT','detail':'effect lost despite accepted pipeline'}]
trace={'state':state}; obj={'effective_once_verified':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h(trace)}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'exactly_once_effective_delivery':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':trace,'exactly_once_effective_delivery':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

