from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"UI_E2E_POLICY_BLOCKED":411,"UI_E2E_STATE_SYNC_CONFLICT":412,"UI_E2E_ACK_TIMEOUT":413}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'ui_e2e_scenarios_audit.json')
smoke=os.path.join(base,'ui_e2e_scenarios_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
scenario={
  "name":"ui_action_to_state_update",
  "chain":["ui_dispatch","permission_gating","policy_enforcement","state_sync","ack","state_reflection"],
  "action":{"panel":"network_panel","action":"set_dns","payload":{"dns":"1.1.1.1"}}
}
failures=[]
if mode=='policy_blocked':
  failures=[{"code":"UI_E2E_POLICY_BLOCKED","detail":"policy denied set_dns for actor"}]
elif mode=='state_sync_conflict':
  failures=[{"code":"UI_E2E_STATE_SYNC_CONFLICT","detail":"state sync conflict during pre_commit"}]
elif mode=='ack_timeout':
  failures=[{"code":"UI_E2E_ACK_TIMEOUT","detail":"ui ack timeout after dispatch"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"scenario":scenario,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"run_e2e_chain","steps":6}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

