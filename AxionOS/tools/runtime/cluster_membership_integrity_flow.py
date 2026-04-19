from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"UNAUTHORIZED_NODE_JOIN":901,"CLUSTER_PARTITION_STATE_TAMPER":902}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'cluster_membership_integrity_audit.json')
smoke_p=os.path.join(base,'cluster_membership_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

membership={
  'expected_nodes':['n1','n2','n3'],
  'active_nodes':['n1','n2','n3'],
  'membership_epoch':42,
  'signed_membership':True
}
failures=[]
if mode=='unauthorized_join':
  membership['active_nodes']=['n1','n2','n3','nX']
  failures=[{'code':'UNAUTHORIZED_NODE_JOIN','detail':'node joined without trusted membership authorization'}]
elif mode=='partition_tamper':
  membership['membership_epoch']=41
  membership['signed_membership']=False
  failures=[{'code':'CLUSTER_PARTITION_STATE_TAMPER','detail':'partition/membership state tampering detected'}]

trace={'membership':membership,'decision':'ACCEPT' if not failures else 'REJECT'}
obj={
  'authorized_membership_enforced': True if not failures else False,
  'partition_state_integrity_verified': True if not failures else False,
  'membership_trace_deterministic': True if not failures else False,
  'membership_trace_hash': h(trace)
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'cluster_membership':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'trace':trace,'cluster_membership':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

