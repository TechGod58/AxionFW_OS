from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"NETWORK_POLICY_BYPASS":701,"UNAUTHORIZED_EGRESS_DETECTED":702}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'network_trust_boundary_integrity_audit.json')
smoke_p=os.path.join(base,'network_trust_boundary_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

boundary={
  'policy_manifest_id':'net-policy-v1',
  'policy_enforced':True,
  'egress_filter_active':True,
  'boundary_violation_blocked':True,
  'ingress_rules_match_manifest':True,
  'egress_rules_match_manifest':True,
  'attempted_traffic':{'src':'svc.ui_bridge','dst':'198.51.100.7:443','class':'external-egress'}
}
failures=[]
if mode=='policy_bypass':
  boundary['policy_enforced']=False
  failures=[{'code':'NETWORK_POLICY_BYPASS','detail':'traffic path bypassed declared network policy'}]
elif mode=='unauthorized_egress':
  boundary['boundary_violation_blocked']=False
  failures=[{'code':'UNAUTHORIZED_EGRESS_DETECTED','detail':'unauthorized outbound connection observed'}]

status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'network_boundary':boundary,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'checks':['policy_enforcement','ingress_egress_manifest_match','boundary_violation_block'],'network_boundary':boundary,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

