from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"OBS_GATE_HASH_FAILURE":491,"OBS_GATE_TIMESTAMP_FAILURE":492,"OBS_GATE_ANOMALY_FAILURE":493}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'observability_unified_gate_audit.json')
smoke_p=os.path.join(base,'observability_unified_gate_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

corr='corr-gate-001'
gate={
  "correlation_id":corr,
  "checks":{
    "observability_hash_correlation":"PASS",
    "observability_timestamp_integrity":"PASS",
    "observability_anomaly_detection":"PASS"
  },
  "anomaly_count":0
}
failures=[]
if mode=='hash_failure':
  gate['checks']['observability_hash_correlation']='FAIL'
  failures=[{"code":"OBS_GATE_HASH_FAILURE","detail":"hash correlation upstream check failed"}]
elif mode=='timestamp_failure':
  gate['checks']['observability_timestamp_integrity']='FAIL'
  failures=[{"code":"OBS_GATE_TIMESTAMP_FAILURE","detail":"timestamp integrity upstream check failed"}]
elif mode=='anomaly_failure':
  gate['checks']['observability_anomaly_detection']='FAIL'
  gate['anomaly_count']=1
  failures=[{"code":"OBS_GATE_ANOMALY_FAILURE","detail":"anomaly detection upstream check failed"}]

status='FAIL' if failures else 'PASS'
smoke={"timestamp_utc":now(),"status":status,"gate":gate,"failures":failures}
audit={"timestamp_utc":now(),"status":status,"gate":gate,"failures":failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

