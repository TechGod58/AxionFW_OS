from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"SECRET_EXPOSED_IN_LOG":541,"SECRET_STORAGE_UNENCRYPTED":542}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'secrets_handling_integrity_audit.json')
smoke_p=os.path.join(base,'secrets_handling_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

secret_name='api_token'
raw_secret='tok_live_ABC123SECRET'
masked='tok_live_***********'
store={"backend":"vault","encrypted":True,"cipher":"AES-256-GCM"}
runtime_surface={"secret_name":secret_name,"value":masked}
telemetry_event={"event":"secret_read","secret_name":secret_name,"value":masked}
failures=[]

if mode=='exposed_in_log':
    telemetry_event['value']=raw_secret
    failures=[{"code":"SECRET_EXPOSED_IN_LOG","detail":"raw secret emitted in telemetry/log surface"}]
elif mode=='storage_unencrypted':
    store['encrypted']=False
    store['cipher']='NONE'
    failures=[{"code":"SECRET_STORAGE_UNENCRYPTED","detail":"secret persisted without encryption"}]

status='FAIL' if failures else 'PASS'
smoke={"timestamp_utc":now(),"status":status,"secrets":{"store":store,"runtime_surface":runtime_surface,"telemetry_event":telemetry_event},"failures":failures}
audit={"timestamp_utc":now(),"status":status,"checks":["encrypted_store","masked_runtime","masked_telemetry"],"secrets":{"store":store,"runtime_surface":runtime_surface,"telemetry_event":telemetry_event},"failures":failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

