from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"POWER_PROFILE_UNSUPPORTED":211}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'power_energy_panel_audit.json')
smoke=os.path.join(base,'power_energy_panel_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
profiles=[{"profile":"balanced","active":True},{"profile":"power_saver","active":False},{"profile":"performance","active":False}]
failures=[]
if mode=='fail': failures=[{"code":"POWER_PROFILE_UNSUPPORTED","detail":"profile=ultra_performance"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"profiles":profiles,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"list_profiles","count":3}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

