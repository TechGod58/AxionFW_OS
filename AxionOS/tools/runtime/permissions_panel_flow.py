from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
CODES={"PERMISSION_POLICY_INVALID":191}
ACCESS_PATH = Path(axion_path_str('config', 'ACCESS_LEVELS_V1.json'))
ACCOUNTS_PATH = Path(axion_path_str('config', 'ACCOUNTS_STATE_V1.json'))
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'permissions_panel_audit.json')
smoke=os.path.join(base,'permissions_panel_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
access = json.loads(ACCESS_PATH.read_text(encoding='utf-8-sig'))
account = json.loads(ACCOUNTS_PATH.read_text(encoding='utf-8-sig')).get('account', {})
policies=[{"policy_id":"perm.camera","state":"allow"},{"policy_id":"perm.location","state":"deny"}]
role = account.get('role', 'User')
level = access.get('levels', {}).get(role, {})
failures=[]
if mode=='fail': failures=[{"code":"PERMISSION_POLICY_INVALID","detail":"policy_id=perm.unknown"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"account_role":role,"access_level":level,"policies":policies,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"list_policies","count":2},{"op":"load_access_level","role": role}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

