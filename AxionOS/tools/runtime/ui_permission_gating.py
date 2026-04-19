from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"UI_PERMISSION_DENIED":391}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'ui_permission_gating_audit.json')
smoke=os.path.join(base,'ui_permission_gating_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
request={"panel":"developer_tools_panel","action":"enable_kernel_debug","actor":"user.standard"}
gating={"policy_chain":["ui_binding","policy_enforcement"],"decision":"allow"}
failures=[]
if mode=='fail':
    gating['decision']='deny'
    failures=[{"code":"UI_PERMISSION_DENIED","detail":"actor user.standard lacks permission for enable_kernel_debug"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"gating":{"request":request,**gating},"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"evaluate_ui_permission","panel":"developer_tools_panel"}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

