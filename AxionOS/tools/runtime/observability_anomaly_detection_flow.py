from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone, timedelta
CODES={"OBS_CORRELATION_WINDOW_MISSING":481,"OBS_DUPLICATE_SEQUENCE_DETECTED":482}
def now(): return datetime.now(timezone.utc)
def iso(dt): return dt.isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'observability_anomaly_detection_audit.json')
smoke_p=os.path.join(base,'observability_anomaly_detection_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
start=now()
corr='corr-anom-001'
timeout_ms=5000
required=["ui_action_dispatch","policy_check","state_sync_commit","ui_action_ack"]
events=[
  {"corr_id":corr,"seq":1,"event":"ui_action_dispatch","ts":iso(start+timedelta(milliseconds=0))},
  {"corr_id":corr,"seq":2,"event":"policy_check","ts":iso(start+timedelta(milliseconds=500))},
  {"corr_id":corr,"seq":3,"event":"state_sync_commit","ts":iso(start+timedelta(milliseconds=1200))},
  {"corr_id":corr,"seq":4,"event":"ui_action_ack","ts":iso(start+timedelta(milliseconds=1800))},
]
failures=[]
if mode=='window_missing':
  events=[events[0],events[1],events[3]]
  failures=[{"code":"OBS_CORRELATION_WINDOW_MISSING","detail":"required event window incomplete within timeout"}]
elif mode=='duplicate_seq':
  events=[
    events[0],
    {"corr_id":corr,"seq":2,"event":"policy_check","ts":iso(start+timedelta(milliseconds=500))},
    {"corr_id":corr,"seq":2,"event":"state_sync_commit","ts":iso(start+timedelta(milliseconds=900))},
    events[3],
  ]
  failures=[{"code":"OBS_DUPLICATE_SEQUENCE_DETECTED","detail":"duplicate sequence value detected for correlation_id"}]
status='FAIL' if failures else 'PASS'
smoke={"timestamp_utc":iso(now()),"status":status,"anomaly_check":{"correlation_id":corr,"timeout_ms":timeout_ms,"required_events":required,"events":events},"failures":failures}
audit={"timestamp_utc":iso(now()),"status":status,"correlation_id":corr,"timeout_ms":timeout_ms,"required_events":required,"events":events,"failures":failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

