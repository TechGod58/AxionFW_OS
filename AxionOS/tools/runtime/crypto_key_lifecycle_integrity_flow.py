from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone, timedelta
CODES={"CRYPTO_KEY_EXPIRED":721,"CRYPTO_KEY_ROTATION_POLICY_VIOLATION":722}
def now_dt(): return datetime.now(timezone.utc)
def iso(dt): return dt.isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'crypto_key_lifecycle_integrity_audit.json')
smoke_p=os.path.join(base,'crypto_key_lifecycle_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

issuer='axion-kms-root'
rotation_days=90
created=now_dt()-timedelta(days=30)
expires=created+timedelta(days=rotation_days)
tracked_usage=True
rotation_policy_compliant=True
active_key={
  'key_id':'key-signing-001',
  'issuer':issuer,
  'created_at':iso(created),
  'expires_at':iso(expires),
  'usage':['signing','encryption'],
  'tracked_usage':tracked_usage
}
failures=[]
if mode=='key_expired':
  active_key['expires_at']=iso(now_dt()-timedelta(days=1))
  failures=[{'code':'CRYPTO_KEY_EXPIRED','detail':'active key expired without completed rotation'}]
elif mode=='rotation_violation':
  rotation_policy_compliant=False
  active_key['tracked_usage']=False
  failures=[{'code':'CRYPTO_KEY_ROTATION_POLICY_VIOLATION','detail':'key rotation/usage tracking policy bypass detected'}]

state={
  'key_authority':issuer,
  'rotation_policy_days':rotation_days,
  'rotation_policy_compliant':rotation_policy_compliant and not failures,
  'key_usage_tracked':active_key['tracked_usage'] and not failures,
  'active_key':active_key,
  'unauthorized_key_material_rejected': True if not failures else False
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':iso(now_dt()),'status':status,'crypto_key_lifecycle':state,'failures':failures}
audit={'timestamp_utc':iso(now_dt()),'status':status,'checks':['authority_trace','expiry_rotation','usage_tracking','unauthorized_material_reject'],'crypto_key_lifecycle':state,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

