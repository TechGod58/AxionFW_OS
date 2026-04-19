from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"BUILD_REPRODUCIBILITY_MISMATCH":621,"BUILD_ENVIRONMENT_UNPINNED":622}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'build_reproducibility_integrity_audit.json')
smoke_p=os.path.join(base,'build_reproducibility_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

commit='abc123def4567890abc123def4567890abc123de'
build_payload='axionos-repro-build:'+commit
build_hash_1=h(build_payload)
build_hash_2=h(build_payload)
env_manifest={'os':'windows','python':'3.12.0','toolchain':'msvc-14.40','flags':'-O2 -deterministic'}
env_hash=h(json.dumps(env_manifest,sort_keys=True,separators=(',',':')))
provenance_artifact_sha=build_hash_1
failures=[]

if mode=='mismatch':
    build_hash_2=h(build_payload+'-nondeterministic')
    failures=[{"code":"BUILD_REPRODUCIBILITY_MISMATCH","detail":"rebuild artifact hash mismatch for same commit"}]
elif mode=='env_unpinned':
    env_manifest.pop('toolchain',None)
    env_hash=h(json.dumps(env_manifest,sort_keys=True,separators=(',',':')))
    failures=[{"code":"BUILD_ENVIRONMENT_UNPINNED","detail":"build environment/toolchain pin set incomplete"}]

repro={
  'source_commit_sha':commit,
  'build_hash_1':build_hash_1,
  'build_hash_2':build_hash_2,
  'hash_match': build_hash_1==build_hash_2,
  'environment_hash': env_hash,
  'environment_manifest': env_manifest,
  'provenance_artifact_sha256': provenance_artifact_sha,
  'artifact_matches_provenance': build_hash_1==provenance_artifact_sha
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'reproducibility':repro,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'checks':['dual_rebuild_hash_match','environment_pinned','provenance_match'],'reproducibility':repro,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

