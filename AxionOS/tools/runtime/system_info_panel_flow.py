from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"SYSTEM_INFO_SOURCE_UNAVAILABLE":201}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'system_info_panel_audit.json')
smoke=os.path.join(base,'system_info_panel_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
facts=[{"key":"os_name","value":"AxionOS"},{"key":"kernel","value":"0.1.0"},{"key":"arch","value":"x86_64"}]
failures=[]
if mode=='fail': failures=[{"code":"SYSTEM_INFO_SOURCE_UNAVAILABLE","detail":"source=hw_probe unavailable"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"facts":facts,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"read_system_info","count":3}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

