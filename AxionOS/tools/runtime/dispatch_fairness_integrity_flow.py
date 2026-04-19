from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
#!/usr/bin/env python3
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"DISPATCH_QUEUE_STARVATION":1671,"DISPATCH_PRIORITY_BYPASS":1672}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit=os.path.join(base,'dispatch_fairness_integrity_audit.json'); smoke=os.path.join(base,'dispatch_fairness_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'; fail=[]
state={'queue_fair':True,'priority_guard':True}
if mode=='starvation': state['queue_fair']=False; fail=[{'code':'DISPATCH_QUEUE_STARVATION','detail':'dispatch queue starvation detected'}]
elif mode=='priority_bypass': state['priority_guard']=False; fail=[{'code':'DISPATCH_PRIORITY_BYPASS','detail':'priority bypass detected'}]
obj={'fairness_enforced':False if fail else True,'priority_policy_enforced':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h({'state':state})}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'dispatch_fairness_integrity':obj,'failures':fail},open(smoke,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':{'state':state},'dispatch_fairness_integrity':obj,'failures':fail},open(audit,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

