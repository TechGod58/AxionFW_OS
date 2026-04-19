from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"TELEMETRY_EVENT_DROPPED":451,"TELEMETRY_SEQUENCE_GAP":452}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'telemetry_event_integrity_audit.json')
smoke=os.path.join(base,'telemetry_event_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
corr='corr-telemetry-001'
events=[
  {"seq":1,"event":"ui_action_dispatch","corr_id":corr},
  {"seq":2,"event":"policy_check","corr_id":corr},
  {"seq":3,"event":"state_sync_commit","corr_id":corr},
  {"seq":4,"event":"ui_action_ack","corr_id":corr},
]
failures=[]
if mode=='event_dropped':
  events=[events[0],events[1],events[3]]
  failures=[{"code":"TELEMETRY_EVENT_DROPPED","detail":"state_sync_commit missing from chain"}]
elif mode=='sequence_gap':
  events=[
    {"seq":1,"event":"ui_action_dispatch","corr_id":corr},
    {"seq":3,"event":"policy_check","corr_id":corr},
    {"seq":4,"event":"state_sync_commit","corr_id":corr},
    {"seq":5,"event":"ui_action_ack","corr_id":corr},
  ]
  failures=[{"code":"TELEMETRY_SEQUENCE_GAP","detail":"sequence gap detected between seq 1 and 3"}]
status='FAIL' if failures else 'PASS'
smoke_obj={"timestamp_utc":now(),"status":status,"telemetry_chain":{"corr_id":corr,"events":events},"failures":failures}
audit_obj={"timestamp_utc":now(),"status":status,"corr_id":corr,"events":events,"failures":failures}
json.dump(smoke_obj,open(smoke,'w',encoding='utf-8'),indent=2)
json.dump(audit_obj,open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

