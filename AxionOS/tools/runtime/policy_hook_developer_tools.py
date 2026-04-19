from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"POLICY_DEVTOOLS_BLOCKED":281}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'policy_hook_developer_tools_audit.json')
smoke=os.path.join(base,'policy_hook_developer_tools_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
request={"tool":"kernel_debug","action":"enable"}
failures=[]
if mode=='fail':
    failures=[{"code":"POLICY_DEVTOOLS_BLOCKED","detail":"kernel_debug enable denied by deny_devtools_kernel_debug"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"request":request,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"evaluate_devtools_policy","tool":"kernel_debug"}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

