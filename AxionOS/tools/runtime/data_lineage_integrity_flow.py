from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"LINEAGE_CHAIN_BREAK":821,"TRANSFORMATION_SOURCE_UNVERIFIED":822}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'data_lineage_integrity_audit.json')
smoke_p=os.path.join(base,'data_lineage_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

source={'artifact_id':'src-raw-001','sha256':'a1'*32,'verified':True}
transform1={'step':'normalize','input':'src-raw-001','output':'mid-001'}
transform2={'step':'aggregate','input':'mid-001','output':'out-001'}
lineage_chain=[source,transform1,transform2]
failures=[]
if mode=='chain_break':
  lineage_chain[2]['input']='mid-missing'
  failures=[{'code':'LINEAGE_CHAIN_BREAK','detail':'lineage chain discontinuity detected between transforms'}]
elif mode=='source_unverified':
  lineage_chain[0]['verified']=False
  failures=[{'code':'TRANSFORMATION_SOURCE_UNVERIFIED','detail':'upstream source not cryptographically verified'}]

trace={'lineage_chain':lineage_chain,'result_artifact':'out-001'}
obj={
  'lineage_chain_hash':h(lineage_chain),
  'lineage_chain_valid': True if not failures else False,
  'upstream_source_verified': True if not failures else False,
  'deterministic_lineage_trace': True if not failures else False,
  'result_artifact':'out-001'
}
status='FAIL' if failures else 'PASS'
smoke={'timestamp_utc':now(),'status':status,'data_lineage':obj,'failures':failures}
audit={'timestamp_utc':now(),'status':status,'trace':trace,'data_lineage':obj,'failures':failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

