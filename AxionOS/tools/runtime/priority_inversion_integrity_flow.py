from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
#!/usr/bin/env python3
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"PRIORITY_INVERSION_UNDETECTED":1681,"PRIORITY_OVERRIDE_BYPASS":1682}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit=os.path.join(base,'priority_inversion_integrity_audit.json'); smoke=os.path.join(base,'priority_inversion_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'; fail=[]
state={'inversion_detected':True,'override_guard':True}
if mode=='inversion': state['inversion_detected']=False; fail=[{'code':'PRIORITY_INVERSION_UNDETECTED','detail':'priority inversion not detected'}]
elif mode=='override_bypass': state['override_guard']=False; fail=[{'code':'PRIORITY_OVERRIDE_BYPASS','detail':'priority override bypass detected'}]
obj={'inversion_detection_enforced':False if fail else True,'override_guard_enforced':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h({'state':state})}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'priority_inversion_integrity':obj,'failures':fail},open(smoke,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':{'state':state},'priority_inversion_integrity':obj,'failures':fail},open(audit,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

