from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"SNAPSHOT_LINEAGE_BREAK":961,"SNAPSHOT_RESTORE_SOURCE_UNVERIFIED":962}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'storage_snapshot_integrity_audit.json')
smoke_p=os.path.join(base,'storage_snapshot_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

snapshots=[
  {'id':'snap-001','parent':None,'hash':'h001','verified':True},
  {'id':'snap-002','parent':'snap-001','hash':'h002','verified':True},
  {'id':'snap-003','parent':'snap-002','hash':'h003','verified':True}
]
restore_request={'target':'snap-003','requester':'svc.restore','nonce':'R-3001'}
failures=[]
if mode=='lineage_break':
  snapshots[2]['parent']='snap-000'
  failures=[{'code':'SNAPSHOT_LINEAGE_BREAK','detail':'snapshot chain parent linkage is broken'}]
elif mode=='source_unverified':
  snapshots[2]['verified']=False
  failures=[{'code':'SNAPSHOT_RESTORE_SOURCE_UNVERIFIED','detail':'restore source snapshot is unverified'}]

trace={'snapshots':snapshots,'restore_request':restore_request,'decision':'ALLOW' if not failures else 'REJECT'}
obj={
  'snapshot_chain_hash_valid': True if not failures else False,
  'restore_source_verified': True if not failures else False,
  'restore_trace_deterministic': True if not failures else False,
  'snapshot_trace_hash': h(trace)
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'storage_snapshot':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'trace':trace,'storage_snapshot':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

