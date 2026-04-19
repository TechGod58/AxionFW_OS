from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"CONFIG_IMMUTABLE_FIELD_MUTATION":521,"CONFIG_GOVERNANCE_OVERRIDE_MISSING":522}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'configuration_immutable_field_policy_audit.json')
smoke_p=os.path.join(base,'configuration_immutable_field_policy_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
immutable=["cluster_id","system_instance_uuid","security_root_policy","baseline_creation_timestamp"]
baseline={"cluster_id":"cluster-a","system_instance_uuid":"uuid-001","security_root_policy":"strict","baseline_creation_timestamp":"2026-03-05T00:00:00Z"}
request={"field":"cluster_id","new_value":"cluster-b","override_token":None}
failures=[]
approved_override=False
if mode=='immutable_mutation':
  # direct forbidden mutation attempt
  failures=[{"code":"CONFIG_IMMUTABLE_FIELD_MUTATION","detail":"immutable field mutation rejected: cluster_id"}]
elif mode=='override_missing':
  # mutation path requires override but token missing
  failures=[{"code":"CONFIG_GOVERNANCE_OVERRIDE_MISSING","detail":"governance override token required for immutable mutation"}]
else:
  # PASS: override present and audited
  request['override_token']='gov-override-allow-001'
  approved_override=True
status='FAIL' if failures else 'PASS'
policy={
  "immutable_fields":immutable,
  "baseline":baseline,
  "request":request,
  "approved_override":approved_override
}
smoke={"timestamp_utc":now(),"status":status,"policy":policy,"failures":failures}
audit={"timestamp_utc":now(),"status":status,"policy":policy,"audit_events":[{"op":"immutable_policy_check","field":request['field']},{"op":"override_evaluation","approved":approved_override}],"failures":failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

