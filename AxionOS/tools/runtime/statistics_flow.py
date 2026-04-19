from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

APPS_STATE = Path(axion_path_str('config', 'APPS_STATE_V1.json'))
CODES={"STATISTICS_NOT_AVAILABLE":361}

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime')
os.makedirs(base,exist_ok=True)
out=os.path.join(base,'statistics_smoke.json')
audit=os.path.join(base,'statistics_audit.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
failures=[]
if mode=='fail': failures=[{"code":"STATISTICS_NOT_AVAILABLE","detail":"statistics host unavailable"}]
apps = json.loads(APPS_STATE.read_text(encoding='utf-8-sig'))
startup_apps = sorted([app_id for app_id, enabled in apps.get('permissions', {}).get('startup', {}).items() if enabled])
processes=[{"pid":1,"name":"svc.shell"},{"pid":2,"name":"svc.eventbus"}]
status='FAIL' if failures else 'PASS'
obj={"timestamp_utc":now(),"status":status,"label":"Statistics","processes":processes,"startup_apps":startup_apps,"failures":failures}
json.dump(obj,open(out,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"events":[{"op":"snapshot_statistics","count":len(processes)},{"op":"startup_apps_loaded","count":len(startup_apps)}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(out)

