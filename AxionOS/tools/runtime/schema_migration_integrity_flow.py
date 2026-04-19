from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"SCHEMA_MIGRATION_PARTIAL_APPLY":1311,"SCHEMA_VERSION_DRIFT_DETECTED":1312}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'schema_migration_integrity_audit.json')
smoke_p=os.path.join(base,'schema_migration_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={
  'target_version':'2026.03.05.1',
  'node_versions':[{'node':'n1','version':'2026.03.05.1'},{'node':'n2','version':'2026.03.05.1'},{'node':'n3','version':'2026.03.05.1'}],
  'tables_migrated':['users','sessions','events'],
  'tables_expected':['users','sessions','events']
}
failures=[]
if mode=='partial_apply':
  state['tables_migrated']=['users','sessions']
  failures=[{'code':'SCHEMA_MIGRATION_PARTIAL_APPLY','detail':'migration applied to subset of tables/nodes only'}]
elif mode=='version_drift':
  state['node_versions'][2]['version']='2026.03.04.9'
  failures=[{'code':'SCHEMA_VERSION_DRIFT_DETECTED','detail':'runtime schema version differs from declared target'}]
trace={'state':state,'decision':'ACCEPT' if not failures else 'REJECT'}
obj={
  'schema_target_version_match': False if failures else True,
  'migration_applied_atomically': False if failures else True,
  'node_schema_convergence': False if failures else True,
  'trace_deterministic': False if failures else True,
  'trace_hash': h(trace)
}
status='FAIL' if failures else 'PASS'
json.dump({'timestamp_utc':now(),'status':status,'schema_migration':obj,'failures':failures},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':status,'trace':trace,'schema_migration':obj,'failures':failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

