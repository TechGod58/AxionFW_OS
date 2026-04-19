from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"POLICY_BACKUP_RESTORE_BLOCKED":291}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'policy_hook_backup_restore_audit.json')
smoke=os.path.join(base,'policy_hook_backup_restore_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
request={"operation":"restore","target":"snapshot:unsigned-2026-03-01"}
failures=[]
if mode=='fail':
    failures=[{"code":"POLICY_BACKUP_RESTORE_BLOCKED","detail":"restore blocked by deny_restore_from_unverified_snapshot"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"request":request,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"evaluate_backup_restore_policy","operation":"restore"}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

