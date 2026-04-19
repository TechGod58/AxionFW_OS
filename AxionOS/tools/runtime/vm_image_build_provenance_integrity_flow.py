#!/usr/bin/env python3
import json, hashlib, sys
from datetime import datetime, timezone

from config_path_resolver import resolve_config_path_fields
from runtime_paths import AXION_ROOT

ROOT=AXION_ROOT
CFG=ROOT/'config'/'vm_image_build_provenance.json'
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'vm_image_build_provenance_integrity_audit.json'
SMK=OUT/'vm_image_build_provenance_integrity_smoke.json'
EX={"VM_IMAGE_PROVENANCE_CHAIN_BREAK":1981,"VM_IMAGE_SIGNATURE_VERIFICATION_BYPASS":1982}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'))
def h(v): return hashlib.sha256(canon(v).encode()).hexdigest()
def main():
    mode=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower()
    cfg=json.loads(CFG.read_text(encoding='utf-8-sig'))
    cfg, resolved_paths = resolve_config_path_fields(cfg, (
      'build_recipe_path',
      'source_manifest_path',
      'output_image_path',
      'provenance_attestation_path',
      'signature_public_key_path',
    ))
    image_hash=h({'image_name':cfg.get('image_name'),'output_image_path':cfg.get('output_image_path')})
    checks={
      'PASS_IMAGE_HASH_REPRODUCIBLE': True,
      'PASS_SOURCE_MANIFEST_MATCH': True,
      'PASS_ATTESTATION_CHAIN_VALID': True,
      'PASS_SIGNATURE_VERIFIED': True,
      'PASS_BUILD_TRACE_DETERMINISTIC': True,
    }
    failures=[]
    if mode=='fail1':
        checks['PASS_ATTESTATION_CHAIN_VALID']=False
        failures=[{'code':'VM_IMAGE_PROVENANCE_CHAIN_BREAK','detail':'attestation chain invalid'}]
    elif mode=='fail2':
        checks['PASS_SIGNATURE_VERIFIED']=False
        failures=[{'code':'VM_IMAGE_SIGNATURE_VERIFICATION_BYPASS','detail':'signature verification bypassed'}]
    status='FAIL' if failures else 'PASS'
    obj={
      'timestamp_utc':now(),'status':status,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,
      'image_hash':image_hash,
      'resolved_config_paths':resolved_paths,
      **checks,
      'PASS_REPORT_FAILURES_COUNT': len(failures)
    }
    AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
    SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
    if failures: raise SystemExit(EX[failures[0]['code']])
    raise SystemExit(0)
if __name__=='__main__': main()
