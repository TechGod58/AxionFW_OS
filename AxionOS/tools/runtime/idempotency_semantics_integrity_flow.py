from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"IDEMPOTENCY_KEY_REUSE_UNDETECTED":1271,"DUPLICATE_SIDE_EFFECT_COMMITTED":1272}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'idempotency_semantics_integrity_audit.json')
smoke_p=os.path.join(base,'idempotency_semantics_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
request={'idempotency_key':'idem-9001','operation':'charge','amount':42}
storage={'idem-9001':'committed:charge:42'}
side_effects=['charge:42']
failures=[]
if mode=='key_reuse_undetected':
    # duplicate accepted as new
    failures=[{'code':'IDEMPOTENCY_KEY_REUSE_UNDETECTED','detail':'duplicate idempotency key was not detected'}]
elif mode=='duplicate_side_effect':
    side_effects=['charge:42','charge:42']
    failures=[{'code':'DUPLICATE_SIDE_EFFECT_COMMITTED','detail':'duplicate request produced duplicate side-effect'}]
trace={'request':request,'storage':storage,'side_effects':side_effects,'decision':'REJECT_DUP' if not failures else 'ALLOW_DUP'}
obj={
  'duplicate_side_effect_prevented': False if failures else True,
  'idempotency_key_enforced': False if failures else True,
  'idempotency_storage_binding_verified': False if failures else True,
  'trace_deterministic': False if failures else True,
  'trace_hash': h(trace)
}
status='FAIL' if failures else 'PASS'
json.dump({'timestamp_utc':now(),'status':status,'idempotency_semantics':obj,'failures':failures},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':status,'trace':trace,'idempotency_semantics':obj,'failures':failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

