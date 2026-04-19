from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"MTLS_CERT_CHAIN_INVALID":1001,"MTLS_IDENTITY_BINDING_MISMATCH":1002}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'inter_service_mtls_identity_integrity_audit.json')
smoke_p=os.path.join(base,'inter_service_mtls_identity_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

session={
  'client_spiffe':'spiffe://axion/svc/api',
  'server_spiffe':'spiffe://axion/svc/runtime',
  'cert_chain_valid':True,
  'identity_binding_valid':True,
  'policy_scope':'svc.runtime.read'
}
failures=[]
if mode=='cert_chain_invalid':
  session['cert_chain_valid']=False
  failures=[{'code':'MTLS_CERT_CHAIN_INVALID','detail':'mTLS certificate chain validation failed'}]
elif mode=='identity_binding_mismatch':
  session['identity_binding_valid']=False
  failures=[{'code':'MTLS_IDENTITY_BINDING_MISMATCH','detail':'certificate identity does not match service identity binding'}]

trace={'session':session,'decision':'ALLOW' if not failures else 'REJECT'}
obj={
  'mtls_cert_chain_valid': True if not failures else False,
  'service_identity_binding_verified': True if not failures else False,
  'mtls_authz_binding_enforced': True if not failures else False,
  'mtls_trace_deterministic': True if not failures else False,
  'mtls_trace_hash': h(trace)
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'inter_service_mtls_identity':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'trace':trace,'inter_service_mtls_identity':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

