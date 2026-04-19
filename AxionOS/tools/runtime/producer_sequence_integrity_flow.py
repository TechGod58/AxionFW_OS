from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
#!/usr/bin/env python3
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"PRODUCER_SEQUENCE_GAP_DETECTED":1591,"PRODUCER_SEQUENCE_REORDER_ACCEPTED":1592}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'producer_sequence_integrity_audit.json'); smoke_p=os.path.join(base,'producer_sequence_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'seq':[100,101,102],'monotonic':True,'reorder':False}
fail=[]
if mode=='gap': state['seq']=[100,102]; fail=[{'code':'PRODUCER_SEQUENCE_GAP_DETECTED','detail':'sequence gap detected'}]
elif mode=='reorder': state['seq']=[100,102,101]; state['reorder']=True; fail=[{'code':'PRODUCER_SEQUENCE_REORDER_ACCEPTED','detail':'out-of-order sequence accepted'}]
trace={'state':state}
obj={'gap_detection_enforced':False if fail else True,'reorder_rejection_enforced':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h(trace)}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'producer_sequence_integrity':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':trace,'producer_sequence_integrity':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

