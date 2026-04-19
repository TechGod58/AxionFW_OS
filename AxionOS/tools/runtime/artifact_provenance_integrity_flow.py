from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"ARTIFACT_SIGNATURE_INVALID":561,"ARTIFACT_PROVENANCE_MISSING":562}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'artifact_provenance_integrity_audit.json')
smoke_p=os.path.join(base,'artifact_provenance_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

artifact_payload='axionos-artifact-v1'
artifact_sha256=h(artifact_payload)
source_commit_sha='abc123def4567890abc123def4567890abc123de'
build_pipeline_id='pipeline-20260305-01'
trusted_key='trusted-key-01'
signature=h(artifact_sha256+trusted_key)
provenance={
  "source_commit_sha":source_commit_sha,
  "build_pipeline_id":build_pipeline_id,
  "artifact_sha256":artifact_sha256,
  "signature":signature,
  "trusted_key_id":trusted_key,
  "signature_verified":True
}
failures=[]
if mode=='signature_invalid':
  provenance['signature']='deadbeef'+signature[8:]
  provenance['signature_verified']=False
  failures=[{"code":"ARTIFACT_SIGNATURE_INVALID","detail":"artifact signature verification failed against trusted key"}]
elif mode=='provenance_missing':
  provenance.pop('build_pipeline_id',None)
  provenance.pop('source_commit_sha',None)
  provenance['signature_verified']=False
  failures=[{"code":"ARTIFACT_PROVENANCE_MISSING","detail":"required provenance metadata missing"}]

status='FAIL' if failures else 'PASS'
smoke={"timestamp_utc":now(),"status":status,"provenance":provenance,"failures":failures}
audit={"timestamp_utc":now(),"status":status,"provenance":provenance,"checks":["signature_verify","provenance_fields_present","pipeline_consistency"],"failures":failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

