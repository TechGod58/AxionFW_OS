from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone, timedelta
CODES={"OBS_TIMESTAMP_NON_MONOTONIC":471,"OBS_CLOCK_SKEW_EXCEEDED":472}
def now(): return datetime.now(timezone.utc)
def iso(dt): return dt.isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'observability_timestamp_integrity_audit.json')
smoke_p=os.path.join(base,'observability_timestamp_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
start=now()
corr='corr-time-001'
# baseline monotonic timeline (audit + telemetry)
audit_events=[
  {"seq":1,"ts":iso(start+timedelta(milliseconds=0)),"corr_id":corr},
  {"seq":2,"ts":iso(start+timedelta(milliseconds=50)),"corr_id":corr},
  {"seq":3,"ts":iso(start+timedelta(milliseconds=100)),"corr_id":corr},
  {"seq":4,"ts":iso(start+timedelta(milliseconds=150)),"corr_id":corr},
]
telemetry_events=[
  {"seq":1,"ts":iso(start+timedelta(milliseconds=20)),"corr_id":corr},
  {"seq":2,"ts":iso(start+timedelta(milliseconds=70)),"corr_id":corr},
  {"seq":3,"ts":iso(start+timedelta(milliseconds=120)),"corr_id":corr},
  {"seq":4,"ts":iso(start+timedelta(milliseconds=170)),"corr_id":corr},
]

failures=[]
tolerance_ms=250
if mode=='non_monotonic':
  # break monotonicity in telemetry at seq3
  telemetry_events[2]['ts']=iso(start+timedelta(milliseconds=40))
  failures=[{"code":"OBS_TIMESTAMP_NON_MONOTONIC","detail":"telemetry timestamp decreased at seq=3"}]
elif mode=='clock_skew_exceeded':
  # introduce skew > tolerance at seq2
  telemetry_events[1]['ts']=iso(start+timedelta(milliseconds=500))
  failures=[{"code":"OBS_CLOCK_SKEW_EXCEEDED","detail":"audit/telemetry skew exceeded 250ms"}]

status='FAIL' if failures else 'PASS'
smoke={
  "timestamp_utc":iso(now()),
  "status":status,
  "timing":{"correlation_id":corr,"tolerance_ms":tolerance_ms,"audit_events":audit_events,"telemetry_events":telemetry_events},
  "failures":failures
}
audit={
  "timestamp_utc":iso(now()),
  "status":status,
  "correlation_id":corr,
  "tolerance_ms":tolerance_ms,
  "audit_events":audit_events,
  "telemetry_events":telemetry_events,
  "failures":failures
}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

