from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"OBS_HASH_MISMATCH":461,"OBS_HASH_MISSING":462}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def sha(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'observability_hash_correlation_audit.json')
smoke_p=os.path.join(base,'observability_hash_correlation_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
correlation_id='corr-obs-001'
payload='{"panel":"network","action":"set_dns","dns":"1.1.1.1"}'
h=sha(payload)
audit={"correlation_id":correlation_id,"payload_sha256":h}
telemetry={"correlation_id":correlation_id,"payload_sha256":h}
failures=[]
if mode=='hash_mismatch':
    telemetry['payload_sha256']=sha(payload+'-drift')
    failures=[{"code":"OBS_HASH_MISMATCH","detail":"audit/telemetry hash mismatch for correlation_id"}]
elif mode=='hash_missing':
    telemetry.pop('payload_sha256',None)
    failures=[{"code":"OBS_HASH_MISSING","detail":"telemetry payload_sha256 missing"}]
status='FAIL' if failures else 'PASS'
smoke={"timestamp_utc":now(),"status":status,"correlation":{"audit":audit,"telemetry":telemetry},"failures":failures}
audit_o={"timestamp_utc":now(),"status":status,"correlation_id":correlation_id,"audit_record":audit,"telemetry_record":telemetry,"failures":failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit_o,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

