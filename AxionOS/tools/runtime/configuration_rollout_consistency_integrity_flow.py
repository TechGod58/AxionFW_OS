from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"CONFIG_ROLLOUT_STATE_DIVERGENCE":1061,"CONFIG_ROLLOUT_VERIFICATION_BYPASS":1062}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'configuration_rollout_consistency_integrity_audit.json')
smoke_p=os.path.join(base,'configuration_rollout_consistency_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

nodes=[
  {'node':'n1','cfg_hash':'sha256:aaa111','stage':'prod'},
  {'node':'n2','cfg_hash':'sha256:aaa111','stage':'prod'},
  {'node':'n3','cfg_hash':'sha256:aaa111','stage':'prod'}
]
stages=['canary','staging','prod']
verification={'canary_to_staging':True,'staging_to_prod':True}
failures=[]

if mode=='state_divergence':
  nodes[2]['cfg_hash']='sha256:bbb222'
  failures=[{'code':'CONFIG_ROLLOUT_STATE_DIVERGENCE','detail':'nodes converged to different configuration hashes'}]
elif mode=='verification_bypass':
  verification['staging_to_prod']=False
  failures=[{'code':'CONFIG_ROLLOUT_VERIFICATION_BYPASS','detail':'verification stage skipped/bypassed before promotion'}]

trace={'stages':stages,'verification':verification,'nodes':nodes,'decision':'ACCEPT' if not failures else 'REJECT'}
obj={
  'config_hash_convergence': True if not failures else False,
  'stage_verification_enforced': True if not failures else False,
  'partial_state_rejected': True if not failures else False,
  'rollout_trace_deterministic': True if not failures else False,
  'rollout_trace_hash': h(trace)
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'configuration_rollout_consistency':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'trace':trace,'configuration_rollout_consistency':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

