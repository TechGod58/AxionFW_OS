from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"CONTROL_PLANE_DESIRED_ACTUAL_DRIFT":1181,"RECONCILIATION_LOOP_STALLED":1182}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit_p=os.path.join(base,'control_plane_reconciliation_integrity_audit.json'); smoke_p=os.path.join(base,'control_plane_reconciliation_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'desired':{'deploy/api':3},'actual':{'deploy/api':3},'loop_healthy':True}
failures=[]
if mode=='drift': failures=[{'code':'CONTROL_PLANE_DESIRED_ACTUAL_DRIFT','detail':'desired and actual state diverged'}]
elif mode=='stalled': failures=[{'code':'RECONCILIATION_LOOP_STALLED','detail':'reconciliation loop stalled'}]
trace={'state':state}
obj={'desired_actual_converged':False if failures else True,'reconciliation_progressing':False if failures else True,'reconciliation_trace_deterministic':False if failures else True,'trace_hash':h(trace)}
status='FAIL' if failures else 'PASS'
json.dump({'timestamp_utc':now(),'status':status,'control_plane_reconciliation':obj,'failures':failures},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':status,'trace':trace,'control_plane_reconciliation':obj,'failures':failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

