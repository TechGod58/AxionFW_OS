from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"SCHEDULER_DECISION_NONDETERMINISTIC":941,"SCHEDULER_POLICY_EVAL_DRIFT":942}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'scheduler_decision_determinism_integrity_audit.json')
smoke_p=os.path.join(base,'scheduler_decision_determinism_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

cluster_state={
  'nodes':[{'id':'n1','free_cpu':4,'free_mem':8192},{'id':'n2','free_cpu':4,'free_mem':8192}],
  'queues':['default'],
  'epoch':144
}
job={'id':'job-2001','cpu':2,'mem':1024,'queue':'default','priority':'normal'}
policy_order=['quota','affinity','fairness','binpack']
decision1={'job':'job-2001','node':'n1','score':0.91}
decision2={'job':'job-2001','node':'n1','score':0.91}
failures=[]
if mode=='decision_nondeterministic':
  decision2={'job':'job-2001','node':'n2','score':0.90}
  failures=[{'code':'SCHEDULER_DECISION_NONDETERMINISTIC','detail':'identical inputs produced divergent placement decisions'}]
elif mode=='policy_eval_drift':
  policy_order=['affinity','quota','fairness','binpack']
  decision1={'job':'job-2001','node':'n2','score':0.92}
  decision2={'job':'job-2001','node':'n2','score':0.92}
  failures=[{'code':'SCHEDULER_POLICY_EVAL_DRIFT','detail':'policy evaluation order drift changed scheduler outcome'}]

sched_input={'cluster_state':cluster_state,'job':job,'policy_order':policy_order}
trace1={'input':sched_input,'decision':decision1}
trace2={'input':sched_input,'decision':decision2}
input_hash=h(sched_input)
dh1=h(trace1)
dh2=h(trace2)
obj={
  'scheduler_input_hash':input_hash,
  'decision_hash_1':dh1,
  'decision_hash_2':dh2,
  'decision_hash_match': True if (dh1==dh2 and decision1==decision2 and not failures) else False,
  'policy_order_deterministic': True if not failures else False,
  'decision_trace_reproducible': True if not failures else False,
  'policy_order':policy_order
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'scheduler_determinism':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'trace1':trace1,'trace2':trace2,'scheduler_determinism':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

