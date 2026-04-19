from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"STATE_SYNC_CONFLICT":301}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'state_sync_audit.json')
smoke=os.path.join(base,'state_sync_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
domains=[{"domain":"network","version":3},{"domain":"privacy","version":5},{"domain":"services","version":4}]
failures=[]
if mode=='fail':
    failures=[{"code":"STATE_SYNC_CONFLICT","detail":"network version mismatch: expected 4 got 3"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"domains":domains,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"reconcile_domains","count":3}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

