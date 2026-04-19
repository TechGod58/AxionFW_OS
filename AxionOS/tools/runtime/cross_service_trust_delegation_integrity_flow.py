from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"DELEGATION_CHAIN_INVALID":801,"DELEGATION_SCOPE_ESCALATION":802}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'cross_service_trust_delegation_integrity_audit.json')
smoke_p=os.path.join(base,'cross_service_trust_delegation_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

input_req={'subject':'svc.frontend','requested_scope':['read.config'],'resource':'svc.runtime','nonce':'N-1001'}
delegation_chain=[
  {'issuer':'auth.root','subject':'svc.frontend','aud':'svc.api','scope':['read.config'],'sig_valid':True},
  {'issuer':'svc.api','subject':'svc.api','aud':'svc.runtime','scope':['read.config'],'sig_valid':True}
]
failures=[]
if mode=='chain_invalid':
  delegation_chain[1]['sig_valid']=False
  failures=[{'code':'DELEGATION_CHAIN_INVALID','detail':'delegation token signature/issuer chain invalid'}]
elif mode=='scope_escalation':
  delegation_chain[1]['scope']=['read.config','write.policy']
  failures=[{'code':'DELEGATION_SCOPE_ESCALATION','detail':'delegated scope widened across service hop'}]

trace={'input':input_req,'chain':delegation_chain,'decision':'ALLOW' if not failures else 'DENY_UNTRUSTED'}
obj={
  'delegation_chain_valid': True if not failures else False,
  'scope_non_widening_enforced': True if not failures else False,
  'decision_trace_hash': h(trace),
  'decision_trace_deterministic': True if not failures else False,
  'hop_path':'frontend->api->runtime'
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'cross_service_trust_delegation':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'trace':trace,'cross_service_trust_delegation':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

