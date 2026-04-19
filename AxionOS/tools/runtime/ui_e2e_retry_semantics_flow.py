from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"UI_E2E_RETRY_EXHAUSTED":421,"UI_E2E_RETRY_POLICY_PERSISTENT":422}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'ui_e2e_retry_semantics_audit.json')
smoke=os.path.join(base,'ui_e2e_retry_semantics_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
scenario={"name":"ui_retry_semantics","max_retries":2,"attempts":[]}
failures=[]

if mode=='retry_exhausted':
    scenario['attempts']=[{"n":1,"result":"transient_failure"},{"n":2,"result":"transient_failure"},{"n":3,"result":"transient_failure"}]
    failures=[{"code":"UI_E2E_RETRY_EXHAUSTED","detail":"all retries exhausted after transient failures"}]
elif mode=='retry_policy_persistent':
    scenario['attempts']=[{"n":1,"result":"policy_denied"},{"n":2,"result":"policy_denied"},{"n":3,"result":"policy_denied"}]
    failures=[{"code":"UI_E2E_RETRY_POLICY_PERSISTENT","detail":"persistent policy denial across retries"}]
else:
    scenario['attempts']=[{"n":1,"result":"transient_failure"},{"n":2,"result":"success"}]

status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"scenario":scenario,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"run_retry_semantics","attempt_count":len(scenario['attempts'])}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

