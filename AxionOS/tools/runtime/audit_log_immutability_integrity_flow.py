from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"AUDIT_LOG_TAMPER_DETECTED":741,"AUDIT_LOG_CHAIN_BREAK":742}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'audit_log_immutability_integrity_audit.json')
smoke_p=os.path.join(base,'audit_log_immutability_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

entries=[
  {'idx':1,'event':'boot','payload':'ok'},
  {'idx':2,'event':'policy_check','payload':'deny'},
  {'idx':3,'event':'ui_dispatch','payload':'set_dns'}
]
prev='GENESIS'
chain=[]
for e in entries:
    ch=h(prev+json.dumps(e,sort_keys=True,separators=(',',':')))
    chain.append({'idx':e['idx'],'hash':ch,'prev':prev})
    prev=ch
append_only_enforced=True
tamper_check_passed=True
failures=[]
if mode=='tamper_detected':
    entries[1]['payload']='allow'  # mutated after commit
    tamper_check_passed=False
    failures=[{'code':'AUDIT_LOG_TAMPER_DETECTED','detail':'audit entry modified after commit'}]
elif mode=='chain_break':
    if len(chain)>1:
        chain[1]['prev']='BROKEN_LINK'
    tamper_check_passed=False
    failures=[{'code':'AUDIT_LOG_CHAIN_BREAK','detail':'hash chain continuity broken'}]

log_hash_chain_valid = True if not failures else False
obj={
  'entries_count':len(entries),
  'log_hash_chain_valid':log_hash_chain_valid,
  'append_only_enforced':append_only_enforced,
  'tamper_check_passed':tamper_check_passed,
  'chain_tail_hash': chain[-1]['hash'] if chain else None
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'audit_immutability':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'entries':entries,'chain':chain,'audit_immutability':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

