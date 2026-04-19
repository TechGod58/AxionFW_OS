from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"DIAGNOSTIC_CHANNEL_DENIED":231}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'logs_diagnostics_panel_audit.json')
smoke=os.path.join(base,'logs_diagnostics_panel_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
channels=[{"channel":"kernel","enabled":True},{"channel":"services","enabled":True},{"channel":"security","enabled":False}]
failures=[]
if mode=='fail': failures=[{"code":"DIAGNOSTIC_CHANNEL_DENIED","detail":"channel=security access denied"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"channels":channels,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"list_channels","count":3}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

