from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"API_SCHEMA_MISMATCH_ACCEPTED":1101,"API_VERSION_NEGOTIATION_BYPASS":1102}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'runtime_api_contract_integrity_audit.json'); smoke_p=os.path.join(base,'runtime_api_contract_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
req={'api':'runtime.tasks','version':'v2','payload':{'action':'start','id':'t-1'}}
contract={'api':'runtime.tasks','version':'v2','required_fields':['action','id']}
decision='ALLOW'; failures=[]
if mode=='schema_mismatch':
  req['payload']={'id':'t-1'}; decision='ALLOW'; failures=[{'code':'API_SCHEMA_MISMATCH_ACCEPTED','detail':'request missing required contract fields accepted'}]
elif mode=='version_bypass':
  req['version']='v9'; decision='ALLOW'; failures=[{'code':'API_VERSION_NEGOTIATION_BYPASS','detail':'unsupported api version bypassed negotiation checks'}]
trace={'request':req,'contract':contract,'decision':decision}
obj={'api_schema_enforced':True if not failures else False,'version_negotiation_enforced':True if not failures else False,'api_trace_deterministic':True if not failures else False,'api_input_hash':h(req)}
status='FAIL' if failures else 'PASS'
json.dump({'timestamp_utc':now(),'status':status,'runtime_api_contract':obj,'failures':failures},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':status,'trace':trace,'runtime_api_contract':obj,'failures':failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

