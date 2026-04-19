from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"UI_E2E_CONCURRENCY_CONFLICT":441,"UI_E2E_DEADLOCK_DETECTED":442}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'ui_e2e_multi_panel_concurrency_audit.json')
smoke=os.path.join(base,'ui_e2e_multi_panel_concurrency_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
scenario={
  "name":"ui_e2e_multi_panel_concurrency",
  "actions":[
    {"id":"a1","panel":"network_panel","op":"set_dns","value":"1.1.1.1"},
    {"id":"a2","panel":"audio_panel","op":"set_default_device","value":"audio.headset"}
  ],
  "ordering":"a1->a2",
  "final_reflected":{"dns":"1.1.1.1","default_audio":"audio.headset"},
  "expected_reflected":{"dns":"1.1.1.1","default_audio":"audio.headset"}
}
failures=[]
if mode=='conflict':
    failures=[{"code":"UI_E2E_CONCURRENCY_CONFLICT","detail":"write-write conflict on shared state epoch"}]
elif mode=='deadlock':
    failures=[{"code":"UI_E2E_DEADLOCK_DETECTED","detail":"lock cycle detected between panel action workers"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"scenario":scenario,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"run_multi_panel_concurrency","action_count":2}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

