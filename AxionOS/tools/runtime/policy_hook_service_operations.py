from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"POLICY_SERVICE_OPERATION_BLOCKED":271}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'policy_hook_service_operations_audit.json')
smoke=os.path.join(base,'policy_hook_service_operations_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
operation={"service_id":"svc.kernel_guard","action":"stop"}
failures=[]
if mode=='fail':
    failures=[{"code":"POLICY_SERVICE_OPERATION_BLOCKED","detail":"stop svc.kernel_guard denied by deny_protected_service_stop"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"operation":operation,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"evaluate_service_operation_policy","service_id":"svc.kernel_guard"}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

