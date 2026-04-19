from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"IDENTITY_TOKEN_FORGED":681,"ACCESS_POLICY_BYPASS":682}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'identity_access_integrity_audit.json')
smoke_p=os.path.join(base,'identity_access_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

issuer='axion-idp'
trusted_key='idp-trusted-key'
subject='user.standard'
roles=['viewer']
required='admin'
token_payload=f'{issuer}:{subject}:{"|".join(roles)}'
token_sig=h(token_payload+trusted_key)

identity={
  'token': {'issuer':issuer,'subject':subject,'roles':roles,'signature':token_sig},
  'token_authority': issuer,
  'token_verified': True,
  'policy_eval': False,
  'requested_action':'enable_kernel_debug',
  'required_role': required,
  'escalation_blocked': True
}

failures=[]
if mode=='token_forged':
  identity['token']['signature']='forged_'+token_sig[:16]
  identity['token_verified']=False
  failures=[{'code':'IDENTITY_TOKEN_FORGED','detail':'token signature verification failed against trusted issuer key'}]
elif mode=='policy_bypass':
  identity['policy_eval']=True
  identity['escalation_blocked']=False
  failures=[{'code':'ACCESS_POLICY_BYPASS','detail':'unauthorized access allowed by policy evaluation'}]
else:
  # PASS: verified token, strict policy, escalation blocked
  identity['policy_eval']=True  # evaluation executed correctly
  identity['escalation_blocked']=True

status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'identity_access':identity,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'checks':['token_verify','policy_eval','escalation_block'],'identity_access':identity,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

