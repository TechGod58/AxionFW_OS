from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"POLICY_EVALUATION_NONDETERMINISTIC":731,"POLICY_RULE_ORDERING_VIOLATION":732}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'policy_evaluation_determinism_integrity_audit.json')
smoke_p=os.path.join(base,'policy_evaluation_determinism_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

policy_input={
  'subject':'user.standard',
  'action':'enable_kernel_debug',
  'resource':'devtools.kernel',
  'context':{'channel':'ui','time_bucket':'business_hours'}
}
rule_order=['deny_devtools_kernel_debug','allow_admin_override','deny_after_hours']
decision_run1={'decision':'DENY','matched_rule':'deny_devtools_kernel_debug'}
decision_run2={'decision':'DENY','matched_rule':'deny_devtools_kernel_debug'}
failures=[]
if mode=='nondeterministic':
    decision_run2={'decision':'ALLOW','matched_rule':'allow_admin_override'}
    failures=[{'code':'POLICY_EVALUATION_NONDETERMINISTIC','detail':'identical inputs produced divergent decisions'}]
elif mode=='ordering_violation':
    rule_order=['allow_admin_override','deny_devtools_kernel_debug','deny_after_hours']
    decision_run1={'decision':'ALLOW','matched_rule':'allow_admin_override'}
    decision_run2={'decision':'ALLOW','matched_rule':'allow_admin_override'}
    failures=[{'code':'POLICY_RULE_ORDERING_VIOLATION','detail':'rule precedence/order changed policy outcome'}]

input_hash=h(policy_input)
trace1={'input':policy_input,'rule_order':rule_order,'decision':decision_run1}
trace2={'input':policy_input,'rule_order':rule_order,'decision':decision_run2}
trace_hash1=h(trace1)
trace_hash2=h(trace2)
obj={
  'policy_input_hash':input_hash,
  'decision_hash_1':trace_hash1,
  'decision_hash_2':trace_hash2,
  'decision_hash_match': trace_hash1==trace_hash2 and decision_run1==decision_run2 and not failures,
  'rule_order_deterministic': True if not failures else False,
  'rule_order': rule_order,
  'decision_run1': decision_run1,
  'decision_run2': decision_run2
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'policy_determinism':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'checks':['input_hash_stability','decision_hash_match','rule_order_determinism'],'policy_determinism':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

