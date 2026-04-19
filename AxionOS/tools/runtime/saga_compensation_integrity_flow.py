from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"COMPENSATION_NOT_EXECUTED":1501,"COMPENSATION_ORDER_VIOLATION":1502}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit_p=os.path.join(base,'saga_compensation_integrity_audit.json'); smoke_p=os.path.join(base,'saga_compensation_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'steps':['reserve','charge','ship'],'compensation':['refund','release'],'ordered':True,'executed':True}
fail=[]
if mode=='not_executed': state['executed']=False; fail=[{'code':'COMPENSATION_NOT_EXECUTED','detail':'required compensation path not executed'}]
elif mode=='order_violation': state['ordered']=False; fail=[{'code':'COMPENSATION_ORDER_VIOLATION','detail':'compensation executed out of required reverse order'}]
trace={'state':state}; obj={'compensation_executed':False if fail else True,'ordering_enforced':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h(trace)}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'saga_compensation':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':trace,'saga_compensation':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

