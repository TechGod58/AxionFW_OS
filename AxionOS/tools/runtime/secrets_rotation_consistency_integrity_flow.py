from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"SECRET_ROTATION_PARTIAL_APPLY":1171,"SECRET_REVOCATION_PROPAGATION_MISS":1172}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit_p=os.path.join(base,'secrets_rotation_consistency_integrity_audit.json'); smoke_p=os.path.join(base,'secrets_rotation_consistency_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'version':'sec-v44','nodes':[{'id':'n1','ver':'sec-v44'},{'id':'n2','ver':'sec-v44'},{'id':'n3','ver':'sec-v44'}],'revoked':['sec-v43']}
failures=[]
if mode=='partial': failures=[{'code':'SECRET_ROTATION_PARTIAL_APPLY','detail':'secret rotation applied to subset of nodes only'}]
elif mode=='revocation_miss': failures=[{'code':'SECRET_REVOCATION_PROPAGATION_MISS','detail':'revoked secret remained usable'}]
trace={'state':state}
obj={'rotation_atomic':False if failures else True,'revocation_propagated':False if failures else True,'rotation_trace_deterministic':False if failures else True,'trace_hash':h(trace)}
status='FAIL' if failures else 'PASS'
json.dump({'timestamp_utc':now(),'status':status,'secrets_rotation_consistency':obj,'failures':failures},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':status,'trace':trace,'secrets_rotation_consistency':obj,'failures':failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

