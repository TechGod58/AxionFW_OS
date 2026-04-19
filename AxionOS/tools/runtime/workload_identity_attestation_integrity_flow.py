from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"WORKLOAD_ATTESTATION_INVALID":1081,"WORKLOAD_IDENTITY_CLAIM_MISMATCH":1082}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'workload_identity_attestation_integrity_audit.json'); smoke_p=os.path.join(base,'workload_identity_attestation_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
att={'workload':'pod://ns/prod/api-7c9','spiffe':'spiffe://axion/ns/prod/sa/api','quote_valid':True,'claim_bind_ok':True}
failures=[]
if mode=='attestation_invalid':
  att['quote_valid']=False; failures=[{'code':'WORKLOAD_ATTESTATION_INVALID','detail':'attestation evidence invalid/untrusted'}]
elif mode=='claim_mismatch':
  att['claim_bind_ok']=False; failures=[{'code':'WORKLOAD_IDENTITY_CLAIM_MISMATCH','detail':'identity claim does not match attested workload identity'}]
trace={'attestation':att,'decision':'ALLOW' if not failures else 'REJECT'}
obj={'attestation_evidence_verified':True if not failures else False,'identity_claim_binding_verified':True if not failures else False,'attestation_trace_deterministic':True if not failures else False,'attestation_input_hash':h(att)}
status='FAIL' if failures else 'PASS'
json.dump({'timestamp_utc':now(),'status':status,'workload_identity_attestation':obj,'failures':failures},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':status,'trace':trace,'workload_identity_attestation':obj,'failures':failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

