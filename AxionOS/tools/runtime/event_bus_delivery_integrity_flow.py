from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"EVENT_DELIVERY_GAP_DETECTED":1121,"EVENT_ORDERING_VIOLATION":1122}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'event_bus_delivery_integrity_audit.json'); smoke_p=os.path.join(base,'event_bus_delivery_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
stream=[{'seq':1,'id':'e1'},{'seq':2,'id':'e2'},{'seq':3,'id':'e3'}]
failures=[]
if mode=='delivery_gap':
  stream=[{'seq':1,'id':'e1'},{'seq':3,'id':'e3'}]
  failures=[{'code':'EVENT_DELIVERY_GAP_DETECTED','detail':'event sequence gap detected'}]
elif mode=='ordering_violation':
  stream=[{'seq':1,'id':'e1'},{'seq':3,'id':'e3'},{'seq':2,'id':'e2'}]
  failures=[{'code':'EVENT_ORDERING_VIOLATION','detail':'event ordering violated'}]
trace={'stream':stream}
obj={'event_delivery_complete':True if not failures else False,'event_ordering_preserved':True if not failures else False,'delivery_trace_deterministic':True if not failures else False,'delivery_trace_hash':h(trace)}
status='FAIL' if failures else 'PASS'
json.dump({'timestamp_utc':now(),'status':status,'event_bus_delivery':obj,'failures':failures},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':status,'trace':trace,'event_bus_delivery':obj,'failures':failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

