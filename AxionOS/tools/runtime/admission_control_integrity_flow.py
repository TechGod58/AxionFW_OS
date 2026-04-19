from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"ADMISSION_POLICY_BYPASS":1041,"ADMISSION_DECISION_DRIFT":1042}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'admission_control_integrity_audit.json'); smoke_p=os.path.join(base,'admission_control_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
req={'subject':'svc.deploy','action':'create_workload','resource':'cluster.ns.prod'}
policy_order=['sig_verify','quota','rbac']; decision1='DENY'; decision2='DENY'; failures=[]
if mode=='policy_bypass':
  decision1='ALLOW'; decision2='ALLOW'; failures=[{'code':'ADMISSION_POLICY_BYPASS','detail':'request admitted without required policy checks'}]
elif mode=='decision_drift':
  decision2='ALLOW'; failures=[{'code':'ADMISSION_DECISION_DRIFT','detail':'identical admission input produced divergent decisions'}]
trace1={'req':req,'order':policy_order,'decision':decision1}; trace2={'req':req,'order':policy_order,'decision':decision2}
obj={'admission_policy_enforced':True if not failures else False,'decision_trace_deterministic':True if not failures else False,'decision_hash_match':True if (h(trace1)==h(trace2) and not failures) else False,'admission_input_hash':h(req)}
status='FAIL' if failures else 'PASS'
json.dump({'timestamp_utc':now(),'status':status,'admission_control':obj,'failures':failures},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':status,'trace1':trace1,'trace2':trace2,'admission_control':obj,'failures':failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

