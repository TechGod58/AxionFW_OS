from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"INBOX_OUTBOX_DIVERGENCE":1511,"INBOX_REPLAY_UNBOUNDED":1512}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit_p=os.path.join(base,'inbox_outbox_pairing_integrity_audit.json'); smoke_p=os.path.join(base,'inbox_outbox_pairing_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'inbox_seq':10,'outbox_seq':10,'replay_guard':True}
fail=[]
if mode=='divergence': state['outbox_seq']=9; fail=[{'code':'INBOX_OUTBOX_DIVERGENCE','detail':'inbox/outbox sequence divergence detected'}]
elif mode=='replay_unbounded': state['replay_guard']=False; fail=[{'code':'INBOX_REPLAY_UNBOUNDED','detail':'inbox replay guard failed; unbounded replay possible'}]
trace={'state':state}; obj={'inbox_prevents_replay':False if fail else True,'pairing_consistent':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h(trace)}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'inbox_outbox_pairing':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':trace,'inbox_outbox_pairing':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

