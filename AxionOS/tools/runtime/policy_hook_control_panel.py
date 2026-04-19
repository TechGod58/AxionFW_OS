from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"POLICY_CONTROL_ACTION_BLOCKED":261}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'policy_hook_control_panel_audit.json')
smoke=os.path.join(base,'policy_hook_control_panel_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
action={"panel":"developer_tools_panel","operation":"set_mode","value":"kernel_debug"}
failures=[]
if mode=='fail':
    failures=[{"code":"POLICY_CONTROL_ACTION_BLOCKED","detail":"operation set_mode=kernel_debug denied by policy"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"action":action,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"evaluate_control_action_policy","panel":"developer_tools_panel"}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

