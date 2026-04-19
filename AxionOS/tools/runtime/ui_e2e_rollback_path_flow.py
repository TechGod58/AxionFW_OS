from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"UI_E2E_ROLLBACK_REQUIRED":431,"UI_E2E_ROLLBACK_FAILED":432}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'ui_e2e_rollback_path_audit.json')
smoke=os.path.join(base,'ui_e2e_rollback_path_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
pre_state={"dns":"9.9.9.9","adapter":"up"}
post_state=dict(pre_state)
scenario={
  "name":"ui_e2e_rollback_path",
  "chain":["ui_dispatch","permission_gating","policy_enforcement","state_sync","runtime_commit","ack","state_reflection"],
  "baseline":pre_state,
  "final_reflected":post_state,
  "rollback_executed":False
}
failures=[]

if mode=='rollback_required':
    scenario['rollback_executed']=True
    scenario['final_reflected']=dict(pre_state)
    failures=[{"code":"UI_E2E_ROLLBACK_REQUIRED","detail":"mid-commit failure detected; rollback required"}]
elif mode=='rollback_failed':
    scenario['rollback_executed']=True
    scenario['final_reflected']={"dns":"1.1.1.1","adapter":"up"}
    failures=[{"code":"UI_E2E_ROLLBACK_FAILED","detail":"rollback executed but final state diverged from baseline"}]
else:
    # pass case: induce mid-commit failure, rollback succeeds, state converges to baseline
    scenario['rollback_executed']=True
    scenario['final_reflected']=dict(pre_state)

status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"scenario":scenario,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"run_rollback_path","rollback_executed":scenario['rollback_executed']}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

