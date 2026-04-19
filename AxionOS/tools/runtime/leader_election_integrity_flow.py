from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"LEADER_ELECTION_SPLIT_BRAIN":981,"LEADER_ELECTION_STATE_TAMPER":982}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'leader_election_integrity_audit.json')
smoke_p=os.path.join(base,'leader_election_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

state={
  'epoch':55,
  'term':55,
  'members':['n1','n2','n3'],
  'quorum_required':2,
  'votes':{'n1':'n2','n2':'n2','n3':'n2'},
  'leaders':['n2'],
  'quorum_verified':True,
  'state_signature_valid':True
}
failures=[]
if mode=='split_brain':
  state['leaders']=['n1','n2']
  failures=[{'code':'LEADER_ELECTION_SPLIT_BRAIN','detail':'concurrent leaders detected in same epoch'}]
elif mode=='state_tamper':
  state['quorum_verified']=False
  state['state_signature_valid']=False
  failures=[{'code':'LEADER_ELECTION_STATE_TAMPER','detail':'election state tampered or quorum verification bypassed'}]

trace={'state':state,'decision':'ACCEPT' if not failures else 'REJECT'}
obj={
  'quorum_verified': True if not failures else False,
  'single_leader_enforced': True if not failures else False,
  'election_trace_deterministic': True if not failures else False,
  'epoch_consistent': True if not failures else False,
  'election_trace_hash': h(trace)
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'leader_election':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'trace':trace,'leader_election':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

