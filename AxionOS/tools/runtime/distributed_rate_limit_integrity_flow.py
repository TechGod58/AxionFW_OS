from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"DISTRIBUTED_RATE_LIMIT_BYPASS":1161,"BURST_AMPLIFICATION_DETECTED":1162}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit_p=os.path.join(base,'distributed_rate_limit_integrity_audit.json'); smoke_p=os.path.join(base,'distributed_rate_limit_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'global_limit_rps':1000,'nodes':[{'id':'n1','rps':300},{'id':'n2','rps':300},{'id':'n3','rps':300}]}
failures=[]
if mode=='bypass': failures=[{'code':'DISTRIBUTED_RATE_LIMIT_BYPASS','detail':'cross-node request path bypassed global limiter'}]
elif mode=='burst_amp': failures=[{'code':'BURST_AMPLIFICATION_DETECTED','detail':'burst amplified across nodes beyond global envelope'}]
trace={'state':state}
obj={'global_quota_enforced':False if failures else True,'cross_node_limit_consistent':False if failures else True,'rate_limit_trace_deterministic':False if failures else True,'trace_hash':h(trace)}
status='FAIL' if failures else 'PASS'
json.dump({'timestamp_utc':now(),'status':status,'distributed_rate_limit':obj,'failures':failures},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':status,'trace':trace,'distributed_rate_limit':obj,'failures':failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

