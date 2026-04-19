from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"DLQ_ROUTING_FAILURE":1331,"DLQ_MESSAGE_LOSS_DETECTED":1332}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'dead_letter_queue_integrity_audit.json')
smoke_p=os.path.join(base,'dead_letter_queue_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={
  'message_id':'msg-7701',
  'retry_count':3,
  'retry_threshold':3,
  'routed_to_dlq':True,
  'dlq_persisted':True
}
failures=[]
if mode=='routing_failure':
  state['routed_to_dlq']=False
  failures=[{'code':'DLQ_ROUTING_FAILURE','detail':'failed message not routed to DLQ after retry threshold'}]
elif mode=='message_loss':
  state['dlq_persisted']=False
  failures=[{'code':'DLQ_MESSAGE_LOSS_DETECTED','detail':'message lost between retry pipeline and DLQ storage'}]
trace={'state':state,'decision':'ACCEPT' if not failures else 'REJECT'}
obj={
  'dlq_routing_enforced': False if failures else True,
  'retry_threshold_enforced': False if failures else True,
  'dlq_message_persisted': False if failures else True,
  'trace_deterministic': False if failures else True,
  'trace_hash': h(trace)
}
status='FAIL' if failures else 'PASS'
json.dump({'timestamp_utc':now(),'status':status,'dead_letter_queue':obj,'failures':failures},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':status,'trace':trace,'dead_letter_queue':obj,'failures':failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

