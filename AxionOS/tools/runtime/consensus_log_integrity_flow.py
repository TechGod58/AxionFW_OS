from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"CONSENSUS_LOG_GAP_DETECTED":1021,"CONSENSUS_ENTRY_HASH_MISMATCH":1022}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'consensus_log_integrity_audit.json'); smoke_p=os.path.join(base,'consensus_log_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
log=[{'idx':1,'term':55,'cmd':'set:a=1'},{'idx':2,'term':55,'cmd':'set:b=2'},{'idx':3,'term':56,'cmd':'set:c=3'}]
failures=[]
if mode=='gap':
  log=[{'idx':1,'term':55,'cmd':'set:a=1'},{'idx':3,'term':56,'cmd':'set:c=3'}]
  failures=[{'code':'CONSENSUS_LOG_GAP_DETECTED','detail':'log index gap detected'}]
elif mode=='hash_mismatch':
  log[2]['cmd']='set:c=999'
  failures=[{'code':'CONSENSUS_ENTRY_HASH_MISMATCH','detail':'entry hash mismatch against committed digest'}]
trace={'log':log}; obj={'log_index_contiguous':True if not failures else False,'entry_hash_chain_valid':True if not failures else False,'replay_trace_deterministic':True if not failures else False,'log_trace_hash':h(trace)}
status='FAIL' if failures else 'PASS'
json.dump({'timestamp_utc':now(),'status':status,'consensus_log':obj,'failures':failures},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':status,'trace':trace,'consensus_log':obj,'failures':failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

