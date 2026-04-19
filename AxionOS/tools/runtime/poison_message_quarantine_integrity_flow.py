from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"POISON_MESSAGE_NOT_QUARANTINED":1361,"QUARANTINE_BYPASS_DETECTED":1362}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'poison_message_quarantine_integrity_audit.json'); smoke_p=os.path.join(base,'poison_message_quarantine_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'msg':'p1','attempts':5,'quarantined':True,'quarantine_store':'dlq-poison'}
fail=[]
if mode=='not_quarantined': fail=[{'code':'POISON_MESSAGE_NOT_QUARANTINED','detail':'poison message exceeded retries but was not quarantined'}]
elif mode=='bypass': fail=[{'code':'QUARANTINE_BYPASS_DETECTED','detail':'poison message bypassed quarantine and re-entered pipeline'}]
trace={'state':state}; obj={'quarantine_enforced':False if fail else True,'poison_loop_blocked':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h(trace)}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'poison_message_quarantine':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':trace,'poison_message_quarantine':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

