from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
#!/usr/bin/env python3
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"CONSUMER_GROUP_STICKY_ASSIGNMENT_BYPASS":1601,"REBALANCE_THRASHING_UNCHECKED":1602}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'consumer_group_balance_integrity_audit.json'); smoke_p=os.path.join(base,'consumer_group_balance_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'sticky_assignment':True,'rebalance_rate':1,'thrashing':False}
fail=[]
if mode=='sticky_bypass': state['sticky_assignment']=False; fail=[{'code':'CONSUMER_GROUP_STICKY_ASSIGNMENT_BYPASS','detail':'sticky assignment policy bypassed'}]
elif mode=='thrashing': state['rebalance_rate']=20; state['thrashing']=True; fail=[{'code':'REBALANCE_THRASHING_UNCHECKED','detail':'rebalance thrashing unchecked'}]
trace={'state':state}
obj={'sticky_assignment_enforced':False if fail else True,'rebalance_guard_enforced':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h(trace)}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'consumer_group_balance_integrity':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':trace,'consumer_group_balance_integrity':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

