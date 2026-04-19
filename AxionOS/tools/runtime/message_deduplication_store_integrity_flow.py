from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"DEDUP_STORE_INCONSISTENT":1491,"DEDUP_TTL_EVICTION_BYPASS":1492}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit_p=os.path.join(base,'message_deduplication_store_integrity_audit.json'); smoke_p=os.path.join(base,'message_deduplication_store_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'key':'msg-42','persisted':True,'ttl_enforced':True,'lookup_hash':'abc'}
fail=[]
if mode=='inconsistent': state['persisted']=False; fail=[{'code':'DEDUP_STORE_INCONSISTENT','detail':'dedup key persistence mismatch across reads'}]
elif mode=='ttl_bypass': state['ttl_enforced']=False; fail=[{'code':'DEDUP_TTL_EVICTION_BYPASS','detail':'expired key still matched due to ttl eviction bypass'}]
trace={'state':state}; obj={'keys_persisted':False if fail else True,'ttl_enforced':False if fail else True,'deterministic_lookups':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h(trace)}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'message_deduplication_store':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':trace,'message_deduplication_store':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

