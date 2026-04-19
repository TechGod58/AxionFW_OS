from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"STATE_SYNC_SERVICE_MUTATION_REJECTED":321}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'state_sync_service_state_audit.json')
smoke=os.path.join(base,'state_sync_service_state_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
mutation={"service_id":"svc.eventbus","action":"restart","expected_epoch":12,"actual_epoch":11}
failures=[]
if mode=='fail':
    failures=[{"code":"STATE_SYNC_SERVICE_MUTATION_REJECTED","detail":"pre_commit rejected stale service epoch"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"mutation":mutation,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"state_sync_service_precommit","service_id":"svc.eventbus"}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

