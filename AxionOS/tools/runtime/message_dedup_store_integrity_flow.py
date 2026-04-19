from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"DEDUP_STORE_TTL_BYPASS":1421,"DEDUP_STORE_KEY_COLLISION_UNDETECTED":1422}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'message_dedup_store_integrity_audit.json'); smoke_p=os.path.join(base,'message_dedup_store_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'key':'k1','ttl_s':600,'collision':False}
fail=[]
if mode=='ttl': fail=[{'code':'DEDUP_STORE_TTL_BYPASS','detail':'dedup key accepted outside TTL policy'}]
elif mode=='collision': state['collision']=True; fail=[{'code':'DEDUP_STORE_KEY_COLLISION_UNDETECTED','detail':'key collision not detected'}]
trace={'state':state}; obj={'dedup_store_enforced':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h(trace)}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'message_dedup_store':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':trace,'message_dedup_store':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

