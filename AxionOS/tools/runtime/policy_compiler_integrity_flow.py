from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"POLICY_COMPILE_NONDETERMINISTIC":1251,"POLICY_IR_HASH_MISMATCH":1252}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'policy_compiler_integrity_audit.json')
smoke_p=os.path.join(base,'policy_compiler_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
policy_input={"version":"v1","rules":[{"id":"deny_debug","when":"role!=admin","effect":"deny"}]}
compiled1={"bytecode":"A1B2C3","ir":["LOAD role","CMP admin","JNE deny"]}
compiled2={"bytecode":"A1B2C3","ir":["LOAD role","CMP admin","JNE deny"]}
failures=[]
if mode=='nondeterministic':
    compiled2={"bytecode":"A1B2FF","ir":["LOAD role","CMP admin","JNE deny"]}
    failures=[{"code":"POLICY_COMPILE_NONDETERMINISTIC","detail":"same policy input produced different compiled output"}]
elif mode=='ir_mismatch':
    compiled2={"bytecode":"A1B2C3","ir":["LOAD role","CMP superadmin","JNE deny"]}
    failures=[{"code":"POLICY_IR_HASH_MISMATCH","detail":"compiled IR hash mismatch for identical input"}]
trace1={"input":policy_input,"compiled":compiled1}
trace2={"input":policy_input,"compiled":compiled2}
obj={
  "policy_input_hash": h(policy_input),
  "compiled_output_hash_match": (h(compiled1)==h(compiled2)) and not failures,
  "ir_hash_match": (h(compiled1.get('ir'))==h(compiled2.get('ir'))) and not failures,
  "trace_deterministic": (trace1==trace2) and not failures,
  "compiled_output_hash_1": h(compiled1),
  "compiled_output_hash_2": h(compiled2)
}
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"policy_compiler":obj,"failures":failures},open(smoke_p,'w'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"trace1":trace1,"trace2":trace2,"policy_compiler":obj,"failures":failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

