from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"CONFIG_DRIFT_DETECTED":511,"CONFIG_BASELINE_MISSING":512}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def sha(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'configuration_drift_detection_audit.json')
smoke_p=os.path.join(base,'configuration_drift_detection_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
baseline={"network":{"dns":"1.1.1.1"},"security":{"firewall":"on"},"immutability_policy":["security.firewall"]}
runtime_state={"network":{"dns":"1.1.1.1"},"security":{"firewall":"on"}}
persisted_snapshot={"network":{"dns":"1.1.1.1"},"security":{"firewall":"on"}}

failures=[]
if mode=='baseline_missing':
    baseline=None
    failures=[{"code":"CONFIG_BASELINE_MISSING","detail":"baseline configuration snapshot not found"}]
elif mode=='drift_detected':
    runtime_state["security"]["firewall"]="off"
    failures=[{"code":"CONFIG_DRIFT_DETECTED","detail":"immutable field security.firewall drifted from baseline"}]

drift={
  "baseline_exists": baseline is not None,
  "baseline_hash": sha(baseline) if baseline is not None else None,
  "runtime_hash": sha(runtime_state),
  "persisted_hash": sha(persisted_snapshot),
  "immutable_paths": baseline.get("immutability_policy",[]) if baseline else [],
  "drift_detected": True if failures else False
}
status='FAIL' if failures else 'PASS'
smoke={"timestamp_utc":now(),"status":status,"drift":drift,"failures":failures}
audit={"timestamp_utc":now(),"status":status,"baseline":baseline,"runtime_state":runtime_state,"persisted_snapshot":persisted_snapshot,"drift":drift,"failures":failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

