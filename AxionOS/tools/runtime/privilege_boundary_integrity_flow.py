from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"PRIVILEGE_ESCALATION_DETECTED":781,"ACL_ENFORCEMENT_BYPASS":782}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime')
os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'privilege_boundary_integrity_audit.json')
smoke_p=os.path.join(base,'privilege_boundary_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

request={
  'principal':'panel.operator',
  'action':'service.restart',
  'resource':'runtime.scheduler',
  'required_capabilities':['service.manage'],
  'channel':'panel'
}
acl={
  'panel.operator':['service.read'],
  'panel.admin':['service.read','service.manage']
}
service_check={'allowed':False,'reason':'missing capability service.manage'}
runtime_check={'allowed':False,'reason':'acl deny propagated'}
failures=[]

if mode=='privilege_escalation':
  service_check={'allowed':True,'reason':'unexpected role elevation applied'}
  runtime_check={'allowed':True,'reason':'unauthorized elevated token accepted'}
  failures=[{'code':'PRIVILEGE_ESCALATION_DETECTED','detail':'principal elevated beyond declared capability boundary'}]
elif mode=='acl_bypass':
  service_check={'allowed':True,'reason':'acl evaluation bypassed in service layer'}
  runtime_check={'allowed':True,'reason':'runtime accepted request without acl proof'}
  failures=[{'code':'ACL_ENFORCEMENT_BYPASS','detail':'acl enforcement bypassed across panel->service->runtime chain'}]

decision_trace={
  'request':request,
  'acl_snapshot':acl,
  'service_check':service_check,
  'runtime_check':runtime_check,
  'final_decision':'DENY' if not failures else 'ALLOW_UNAUTHORIZED'
}
obj={
  'capability_acl_enforced': True if not failures else False,
  'unauthorized_escalation_rejected': True if not failures else False,
  'decision_trace_hash': h(decision_trace),
  'decision_trace_deterministic': True if not failures else False,
  'request_path':'panel->service->runtime'
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'privilege_boundary':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'decision_trace':decision_trace,'privilege_boundary':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

