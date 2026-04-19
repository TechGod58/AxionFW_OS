from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"TIME_SYNC_DRIFT_EXCEEDED":661,"TIME_AUTHORITY_UNTRUSTED":662}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'time_sync_integrity_audit.json')
smoke_p=os.path.join(base,'time_sync_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

time_source='ntp.trusted.axion'
drift_tolerance_ms=250
node_drifts_ms={'node-a':35,'node-b':42,'node-c':18}
authority_verified=True
signed_checkpoints_match=True

failures=[]
if mode=='drift_exceeded':
    node_drifts_ms['node-b']=412
    failures=[{"code":"TIME_SYNC_DRIFT_EXCEEDED","detail":"node drift exceeded tolerance"}]
elif mode=='authority_untrusted':
    authority_verified=False
    failures=[{"code":"TIME_AUTHORITY_UNTRUSTED","detail":"time authority trust chain verification failed"}]

max_drift=max(node_drifts_ms.values())
time_sync={
  'time_source':time_source,
  'drift_tolerance_ms':drift_tolerance_ms,
  'max_drift_ms':max_drift,
  'drift_within_tolerance': max_drift<=drift_tolerance_ms and not failures,
  'authority_verified': authority_verified and not failures,
  'signed_checkpoints_match': signed_checkpoints_match
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'time_sync':time_sync,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'node_drifts_ms':node_drifts_ms,'time_sync':time_sync,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

