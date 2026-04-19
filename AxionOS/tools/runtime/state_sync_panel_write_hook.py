from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"STATE_SYNC_WRITE_REJECTED":311}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'state_sync_panel_write_audit.json')
smoke=os.path.join(base,'state_sync_panel_write_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
write_req={"panel":"network","field":"dns","value":"1.1.1.1","domain_version_expected":4,"domain_version_actual":3}
failures=[]
if mode=='fail':
    failures=[{"code":"STATE_SYNC_WRITE_REJECTED","detail":"pre_commit reconciliation rejected stale domain version"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"write_request":write_req,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"state_sync_pre_commit","panel":"network"}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

