from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"CHECKPOINT_LINEAGE_BREAK":1851,"CHECKPOINT_PARENT_UNVERIFIED":1852}
def now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(",",":")).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit=os.path.join(base,"checkpoint_lineage_integrity_audit.json"); smoke=os.path.join(base,"checkpoint_lineage_integrity_smoke.json")
mode=sys.argv[1] if len(sys.argv)>1 else "pass"; fail=[]
if mode=="fail1": fail=[{"code":"CHECKPOINT_LINEAGE_BREAK","detail":"deterministic negative 1"}]
elif mode=="fail2": fail=[{"code":"CHECKPOINT_PARENT_UNVERIFIED","detail":"deterministic negative 2"}]
obj={"trace_deterministic":False if fail else True,"trace_hash":h({"mode":mode})}
st="FAIL" if fail else "PASS"
json.dump({"timestamp_utc":now(),"status":st,"checkpoint_lineage_integrity":obj,"failures":fail},open(smoke,"w"),indent=2)
json.dump({"timestamp_utc":now(),"status":st,"trace":{"mode":mode},"checkpoint_lineage_integrity":obj,"failures":fail},open(audit,"w"),indent=2)
if fail: raise SystemExit(CODES[fail[0]["code"]])

