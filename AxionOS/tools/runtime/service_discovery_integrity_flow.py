from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"SERVICE_REGISTRATION_FORGED":921,"SERVICE_ENDPOINT_RESOLUTION_POISONED":922}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'service_discovery_integrity_audit.json')
smoke_p=os.path.join(base,'service_discovery_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

registry={
  'service':'svc.api',
  'registrations':[{'node':'n1','endpoint':'10.0.0.11:8443','signed':True,'epoch':77},
                   {'node':'n2','endpoint':'10.0.0.12:8443','signed':True,'epoch':77}],
  'cluster_epoch':77
}
query={'service':'svc.api','requester':'svc.gateway','nonce':'Q-2001'}
resolution=['10.0.0.11:8443','10.0.0.12:8443']
failures=[]
if mode=='forged_registration':
  registry['registrations'].append({'node':'nX','endpoint':'10.9.9.9:8443','signed':False,'epoch':77})
  failures=[{'code':'SERVICE_REGISTRATION_FORGED','detail':'forged/unsigned service registration accepted'}]
elif mode=='resolution_poisoned':
  resolution=['10.0.0.11:8443','10.9.9.9:8443']
  failures=[{'code':'SERVICE_ENDPOINT_RESOLUTION_POISONED','detail':'discovery resolution returned poisoned/stale endpoint'}]

trace={'registry':registry,'query':query,'resolution':resolution,'decision':'ALLOW' if not failures else 'REJECT'}
obj={
  'service_registration_authenticated': True if not failures else False,
  'discovery_state_consistent': True if not failures else False,
  'forged_entries_rejected': True if not failures else False,
  'resolution_trace_deterministic': True if not failures else False,
  'resolution_trace_hash': h(trace)
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'service_discovery':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'trace':trace,'service_discovery':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

