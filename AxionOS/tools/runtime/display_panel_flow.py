from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"DISPLAY_MODE_UNSUPPORTED":171}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'display_panel_audit.json')
smoke=os.path.join(base,'display_panel_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
modes=[{"mode":"1920x1080@60","active":True},{"mode":"1280x720@60","active":False}]
failures=[]
if mode=='fail': failures=[{"code":"DISPLAY_MODE_UNSUPPORTED","detail":"mode=7680x4320@240"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"modes":modes,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"list_modes","count":2}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

