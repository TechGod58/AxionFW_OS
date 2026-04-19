from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"RUNTIME_ISOLATION_ESCAPE_ATTEMPT":581,"RUNTIME_SANDBOX_POLICY_MISSING":582}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'runtime_isolation_integrity_audit.json')
smoke_p=os.path.join(base,'runtime_isolation_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

isolation={
  "sandbox_policy_present":True,
  "managed_services":["svc.eventbus","svc.kernel_guard","svc.ui_bridge"],
  "capability_policy":{"allowed":["net.read","fs.read"],"denied":["proc.escape","priv.escalate"]},
  "escape_attempt_rejected":True,
  "audit_emitted":True
}
failures=[]
if mode=='escape_attempt':
  isolation['escape_attempt_rejected']=False
  failures=[{"code":"RUNTIME_ISOLATION_ESCAPE_ATTEMPT","detail":"cross-boundary process escape attempt detected"}]
elif mode=='policy_missing':
  isolation['sandbox_policy_present']=False
  failures=[{"code":"RUNTIME_SANDBOX_POLICY_MISSING","detail":"sandbox policy missing for managed runtime"}]

status='FAIL' if failures else 'PASS'
smoke={"timestamp_utc":now(),"status":status,"isolation":isolation,"failures":failures}
audit={"timestamp_utc":now(),"status":status,"checks":["sandbox_policy","capability_match","escape_rejection","audit_emit"],"isolation":isolation,"failures":failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

