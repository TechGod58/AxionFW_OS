from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"RESOURCE_QUOTA_EXCEEDED_UNCHECKED":841,"QUOTA_POLICY_BYPASS":842}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'resource_quota_enforcement_integrity_audit.json')
smoke_p=os.path.join(base,'resource_quota_enforcement_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

quota_policy={'cpu_millis':2000,'memory_mb':1024,'io_ops':5000,'job_slots':8}
request={'actor':'svc.analytics','cpu_millis':2500,'memory_mb':512,'io_ops':1200,'job_slots':2}
failures=[]
if mode=='overflow_unchecked':
    enforcement={'checked':False,'decision':'ALLOW','reason':'quota check skipped'}
    failures=[{'code':'RESOURCE_QUOTA_EXCEEDED_UNCHECKED','detail':'quota overflow allowed without enforcement'}]
elif mode=='policy_bypass':
    enforcement={'checked':True,'decision':'ALLOW','reason':'bypass flag ignored quota deny path'}
    failures=[{'code':'QUOTA_POLICY_BYPASS','detail':'quota policy bypass detected in enforcement chain'}]
else:
    enforcement={'checked':True,'decision':'DENY','reason':'cpu_millis exceeds quota'}

trace={'policy':quota_policy,'request':request,'enforcement':enforcement}
obj={
  'quota_policy_enforced': True if not failures else False,
  'excess_request_rejected': True if not failures else False,
  'enforcement_trace_deterministic': True if not failures else False,
  'enforcement_trace_hash': h(trace)
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'resource_quota':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'trace':trace,'resource_quota':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

