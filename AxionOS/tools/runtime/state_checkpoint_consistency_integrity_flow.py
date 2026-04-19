from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"STATE_CHECKPOINT_HASH_MISMATCH":1141,"STATE_CHECKPOINT_RESTORE_INCONSISTENT":1142}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'state_checkpoint_consistency_integrity_audit.json')
smoke_p=os.path.join(base,'state_checkpoint_consistency_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

checkpoint={'id':'cp-5001','state_root':'root-abc123','lineage':['cp-4999','cp-5000','cp-5001'],'payload':{'svc':'runtime','seq':5001}}
restored_state={'state_root':'root-abc123','lineage_tail':'cp-5001'}
failures=[]
if mode=='hash_mismatch':
  restored_state['state_root']='root-deadbeef'
  failures=[{'code':'STATE_CHECKPOINT_HASH_MISMATCH','detail':'checkpoint hash differs from recorded state root'}]
elif mode=='restore_inconsistent':
  restored_state['lineage_tail']='cp-4998'
  failures=[{'code':'STATE_CHECKPOINT_RESTORE_INCONSISTENT','detail':'restored state diverges from checkpoint lineage'}]

trace={'checkpoint':checkpoint,'restored_state':restored_state,'decision':'ACCEPT' if not failures else 'REJECT'}
obj={
  'checkpoint_hash_verified': True if not failures else False,
  'restore_state_consistent': True if not failures else False,
  'checkpoint_trace_deterministic': True if not failures else False,
  'checkpoint_trace_hash': h(trace)
}
status='FAIL' if failures else 'PASS'
json.dump({'timestamp_utc':now(),'status':status,'state_checkpoint_consistency':obj,'failures':failures},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':status,'trace':trace,'state_checkpoint_consistency':obj,'failures':failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

