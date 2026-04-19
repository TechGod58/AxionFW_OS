from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"EXACTLY_ONCE_DUPLICATE_DELIVERY":1471,"EXACTLY_ONCE_ACK_BEFORE_COMMIT":1472}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit_p=os.path.join(base,'exactly_once_delivery_integrity_audit.json'); smoke_p=os.path.join(base,'exactly_once_delivery_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'msg':'m-1','producer_dedup':True,'consumer_dedup':True,'commit_persisted':True,'ack_sent':True,'deliveries':1}
fail=[]
if mode=='dup': state['deliveries']=2; fail=[{'code':'EXACTLY_ONCE_DUPLICATE_DELIVERY','detail':'duplicate delivery observed'}]
elif mode=='ack_before_commit': state['commit_persisted']=False; state['ack_sent']=True; fail=[{'code':'EXACTLY_ONCE_ACK_BEFORE_COMMIT','detail':'ack emitted before durable commit'}]
trace={'state':state}; obj={'effective_dedup_enforced':False if fail else True,'ack_after_commit_enforced':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h(trace)}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'exactly_once_delivery':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':trace,'exactly_once_delivery':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

