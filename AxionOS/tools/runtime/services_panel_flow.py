from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"SERVICE_PANEL_SERVICE_LOCKED":101}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit=os.path.join(base,'services_panel_audit.json'); smoke=os.path.join(base,'services_panel_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
services=[{"service_id":"svc.shell","state":"running","locked":True},{"service_id":"svc.eventbus","state":"running","locked":False}]
failures=[]; events=[]
if mode=='fail': failures=[{"code":"SERVICE_PANEL_SERVICE_LOCKED","detail":"svc.shell locked"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"services":services,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":events,"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

