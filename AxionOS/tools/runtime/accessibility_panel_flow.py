from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"ACCESSIBILITY_FEATURE_INVALID":161}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'accessibility_panel_audit.json')
smoke=os.path.join(base,'accessibility_panel_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
features=[{"feature":"screen_reader","enabled":True},{"feature":"high_contrast","enabled":False}]
failures=[]
if mode=='fail': failures=[{"code":"ACCESSIBILITY_FEATURE_INVALID","detail":"feature=unknown_feature"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"features":features,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"list_features","count":2}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(smoke)

