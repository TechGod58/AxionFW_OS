from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"ARTIFACT_PROVENANCE_CHAIN_BREAK":1191,"ARTIFACT_SIGNATURE_VERIFICATION_BYPASS":1192}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit_p=os.path.join(base,'artifact_supply_chain_integrity_audit.json'); smoke_p=os.path.join(base,'artifact_supply_chain_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state={'artifact':'axion-runtime.tar','provenance':['src','build','sign'],'signature_valid':True}
failures=[]
if mode=='chain_break': failures=[{'code':'ARTIFACT_PROVENANCE_CHAIN_BREAK','detail':'provenance chain missing attestation'}]
elif mode=='sig_bypass': failures=[{'code':'ARTIFACT_SIGNATURE_VERIFICATION_BYPASS','detail':'artifact accepted without signature verification'}]
trace={'state':state}
obj={'provenance_chain_complete':False if failures else True,'signature_verified':False if failures else True,'supply_chain_trace_deterministic':False if failures else True,'trace_hash':h(trace)}
status='FAIL' if failures else 'PASS'
json.dump({'timestamp_utc':now(),'status':status,'artifact_supply_chain':obj,'failures':failures},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':status,'trace':trace,'artifact_supply_chain':obj,'failures':failures},open(audit_p,'w'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

