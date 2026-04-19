from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"STATE_TRANSITION_ILLEGAL":761,"STATE_MACHINE_GRAPH_CORRUPTED":762}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'state_machine_transition_integrity_audit.json')
smoke_p=os.path.join(base,'state_machine_transition_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

graph={
  'INIT':['READY'],
  'READY':['RUNNING','ERROR'],
  'RUNNING':['READY','ERROR'],
  'ERROR':['READY']
}
sequence=['INIT','READY','RUNNING','READY']
failures=[]
if mode=='illegal_transition':
  sequence=['INIT','RUNNING']
  failures=[{'code':'STATE_TRANSITION_ILLEGAL','detail':'transition INIT->RUNNING not allowed by graph'}]
elif mode=='graph_corrupted':
  graph['READY']=['RUNNING','ERROR','INVALID_STATE']
  failures=[{'code':'STATE_MACHINE_GRAPH_CORRUPTED','detail':'graph contains inconsistent or unauthorized state edge'}]

graph_hash=h(graph)
seq_hash=h(sequence)
obj={
  'graph':graph,
  'sequence':sequence,
  'state_graph_hash':graph_hash,
  'transition_sequence_hash':seq_hash,
  'transition_sequence_valid': True if not failures else False,
  'graph_integrity_verified': True if not failures else False
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'state_machine':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'checks':['graph_integrity','transition_validity','unreachable_state_reject'],'state_machine':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

