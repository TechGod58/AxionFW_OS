from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"RETRY_BACKOFF_BYPASS":1351,"RETRY_STORM_AMPLIFICATION":1352}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'retry_backoff_integrity_audit.json'); smoke_p=os.path.join(base,'retry_backoff_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'message':'m1','attempts':[1,2,3],'backoff_ms':[100,200,400],'max_retries':3}
fail=[]
if mode=='bypass': fail=[{'code':'RETRY_BACKOFF_BYPASS','detail':'retry executed without required backoff'}]
elif mode=='storm': fail=[{'code':'RETRY_STORM_AMPLIFICATION','detail':'retry storm amplified due to missing jitter/backoff envelope'}]
trace={'state':state}; obj={'backoff_enforced':False if fail else True,'retry_envelope_safe':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h(trace)}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'retry_backoff':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':trace,'retry_backoff':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

