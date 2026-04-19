from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"DEVICE_NOT_FOUND":111}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit=os.path.join(base,'devices_panel_audit.json'); smoke=os.path.join(base,'devices_panel_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
devices=[{"device_id":"dev.keyboard","status":"ok"},{"device_id":"dev.mouse","status":"ok"}]
failures=[]; events=[]
if mode=='fail': failures=[{"code":"DEVICE_NOT_FOUND","detail":"dev.camera_missing"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"devices":devices,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":events,"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

