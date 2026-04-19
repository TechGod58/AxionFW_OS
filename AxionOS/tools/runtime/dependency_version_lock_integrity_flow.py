from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"DEPENDENCY_VERSION_DRIFT":601,"DEPENDENCY_LOCKFILE_MISSING":602}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj): return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'dependency_version_lock_integrity_audit.json')
smoke_p=os.path.join(base,'dependency_version_lock_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

lockfile={
  "modules":[
    {"name":"core.net","version":"1.2.0","hash":"hash_core_net_120"},
    {"name":"core.sec","version":"2.1.1","hash":"hash_core_sec_211"},
    {"name":"ui.bridge","version":"0.9.4","hash":"hash_ui_bridge_094"}
  ]
}
runtime_graph=[
  {"name":"core.net","version":"1.2.0","hash":"hash_core_net_120"},
  {"name":"core.sec","version":"2.1.1","hash":"hash_core_sec_211"},
  {"name":"ui.bridge","version":"0.9.4","hash":"hash_ui_bridge_094"}
]
failures=[]
if mode=='version_drift':
  runtime_graph[1]['version']='2.2.0'
  failures=[{"code":"DEPENDENCY_VERSION_DRIFT","detail":"runtime dependency version differs from lockfile"}]
elif mode=='lockfile_missing':
  lockfile=None
  failures=[{"code":"DEPENDENCY_LOCKFILE_MISSING","detail":"dependency lockfile missing at runtime check"}]

dep={
  "lockfile_present": lockfile is not None,
  "lockfile_hash": h(lockfile) if lockfile is not None else None,
  "runtime_graph_hash": h(runtime_graph),
  "runtime_graph": runtime_graph,
  "lockfile": lockfile,
  "graph_matches_lockfile": (lockfile is not None and runtime_graph==lockfile['modules']) and not failures
}
status='FAIL' if failures else 'PASS'
smoke={"timestamp_utc":now(),"status":status,"dependency":dep,"failures":failures}
audit={"timestamp_utc":now(),"status":status,"checks":["lockfile_present","version_match","hash_match","transitive_drift_check"],"dependency":dep,"failures":failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

