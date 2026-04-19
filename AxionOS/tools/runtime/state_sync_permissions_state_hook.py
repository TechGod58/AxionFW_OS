from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"STATE_SYNC_PERMISSIONS_MUTATION_REJECTED":331}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'state_sync_permissions_state_audit.json')
smoke=os.path.join(base,'state_sync_permissions_state_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
mutation={"subject":"app.notes","permission":"camera","action":"allow","expected_rev":9,"actual_rev":8}
failures=[]
if mode=='fail':
    failures=[{"code":"STATE_SYNC_PERMISSIONS_MUTATION_REJECTED","detail":"pre_commit rejected stale permissions revision"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"mutation":mutation,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"state_sync_permissions_precommit","subject":"app.notes"}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

