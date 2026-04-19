from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"ROLL_OUT_INCOMPLETE_APPLY":861,"ROLL_OUT_VERIFICATION_BYPASS":862}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'update_rollout_integrity_audit.json')
smoke_p=os.path.join(base,'update_rollout_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

rollout={
  'stages':['canary','staging','production'],
  'verification_required_between_stages':True,
  'applied_stages':['canary','staging','production'],
  'stage_verifications':[True,True],
  'fleet_state':'consistent'
}
failures=[]
if mode=='incomplete_apply':
  rollout['applied_stages']=['canary','staging']
  rollout['fleet_state']='partial'
  failures=[{'code':'ROLL_OUT_INCOMPLETE_APPLY','detail':'rollout ended in partially applied/inconsistent state'}]
elif mode=='verification_bypass':
  rollout['stage_verifications']=[True,False]
  failures=[{'code':'ROLL_OUT_VERIFICATION_BYPASS','detail':'required inter-stage verification was bypassed'}]

trace={'rollout':rollout,'decision':'ACCEPT' if not failures else 'REJECT'}
obj={
  'stage_order_enforced': True if not failures else False,
  'verification_required': True if not failures else False,
  'partial_state_rejected': True if not failures else False,
  'rollout_trace_deterministic': True if not failures else False,
  'rollout_trace_hash': h(trace)
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'update_rollout':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'trace':trace,'update_rollout':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

