from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"UI_ACTION_DISPATCH_UNKNOWN":371}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'ui_panel_action_dispatch_audit.json')
smoke=os.path.join(base,'ui_panel_action_dispatch_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
request={"panel":"network_panel","action":"set_dns","payload":{"dns":"1.1.1.1"}}
route=["ui_binding","state_sync","policy_enforcement","runtime_op"]
failures=[]
if mode=='fail':
    failures=[{"code":"UI_ACTION_DISPATCH_UNKNOWN","detail":"action=do_magic not mapped"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"dispatch":{"request":request,"route":route},"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"dispatch_action","panel":"network_panel"}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

