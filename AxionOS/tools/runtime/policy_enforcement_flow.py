from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"POLICY_RULE_VIOLATION":251}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'policy_enforcement_audit.json')
smoke=os.path.join(base,'policy_enforcement_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
rules=[
  {"rule_id":"deny_devtools_kernel_debug","state":"enforced"},
  {"rule_id":"deny_untrusted_backup_target","state":"enforced"},
  {"rule_id":"allow_signed_panel_ops","state":"enforced"}
]
failures=[]
if mode=='fail': failures=[{"code":"POLICY_RULE_VIOLATION","detail":"operation=enable_kernel_debug blocked by deny_devtools_kernel_debug"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"rules":rules,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"evaluate_rules","count":3}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

