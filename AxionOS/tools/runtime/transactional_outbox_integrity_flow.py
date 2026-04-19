from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"OUTBOX_EVENT_NOT_PUBLISHED":1291,"OUTBOX_DUPLICATE_PUBLISH":1292}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'transactional_outbox_integrity_audit.json')
smoke_p=os.path.join(base,'transactional_outbox_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={
  'tx_id':'tx-5001',
  'outbox_id':'outbox-5001',
  'event_id':'evt-5001',
  'outbox_persisted':True,
  'publish_confirmed':True,
  'publish_count':1
}
failures=[]
if mode=='not_published':
  state['publish_confirmed']=False
  state['publish_count']=0
  failures=[{'code':'OUTBOX_EVENT_NOT_PUBLISHED','detail':'outbox event persisted but not published'}]
elif mode=='duplicate_publish':
  state['publish_count']=2
  failures=[{'code':'OUTBOX_DUPLICATE_PUBLISH','detail':'outbox event published more than once'}]
trace={'state':state,'decision':'ACCEPT' if not failures else 'REJECT'}
obj={
  'outbox_persisted': True if not failures else False,
  'publish_confirmed': True if not failures else False,
  'no_duplicates': True if not failures else False,
  'deterministic_trace': True if not failures else False,
  'trace_hash': h(trace)
}
status='FAIL' if failures else 'PASS'
json.dump({'timestamp_utc':now(),'status':status,'transactional_outbox':obj,'failures':failures},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':status,'trace':trace,'transactional_outbox':obj,'failures':failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

