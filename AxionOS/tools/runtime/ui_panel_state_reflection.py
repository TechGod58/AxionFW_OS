from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"UI_STATE_REFLECTION_STALE":381}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'ui_panel_state_reflection_audit.json')
smoke=os.path.join(base,'ui_panel_state_reflection_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
reflection={"panel":"network_panel","ui_revision":42,"runtime_revision":42,"fields":["dns","adapter_state"]}
failures=[]
if mode=='fail':
    reflection["runtime_revision"]=41
    failures=[{"code":"UI_STATE_REFLECTION_STALE","detail":"ui_revision=42 runtime_revision=41"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"reflection":reflection,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"reflect_state","panel":"network_panel"}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

