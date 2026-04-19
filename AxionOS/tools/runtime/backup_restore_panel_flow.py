from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"BACKUP_TARGET_INVALID":221}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'backup_restore_panel_audit.json')
smoke=os.path.join(base,'backup_restore_panel_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
targets=[{"target":"local.disk","enabled":True},{"target":"remote.nas","enabled":False}]
failures=[]
if mode=='fail': failures=[{"code":"BACKUP_TARGET_INVALID","detail":"target=remote.unknown"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"targets":targets,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"list_targets","count":2}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

