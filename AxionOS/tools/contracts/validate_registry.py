#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, re, sys, subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

try:
    import jsonschema  # type: ignore
except Exception:
    jsonschema = None

EXIT_PASS=0; EXIT_SCHEMA_FAIL=1; EXIT_MISSING_FILE=2; EXIT_HASH_MISMATCH=3; EXIT_REGISTRY_ERROR=4
CATEGORY_ENUM={"schema","marker","policy","compat","fixture"}
REQUIRED_ENTRY_KEYS=("contract_id","category","version","path","sha256")

FW_CODES={
 "FW_HANDOFF_MISSING","FW_HANDOFF_SCHEMA_FAIL","FW_HANDOFF_VERSION_MISMATCH","FW_HANDOFF_PLATFORM_UNKNOWN",
 "FW_HANDOFF_MEMORY_INVALID","FW_HANDOFF_BOOT_VECTOR_INVALID","FW_SUMMARY_MISSING","FW_SUMMARY_NOT_PASS","FW_BOOTLOG_MISSING"
}

def utc_now_iso()->str: return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def load_json(path:str)->Any:
    with open(path,'r',encoding='utf-8-sig') as f: return json.load(f)
def sha256_file(path:str)->str:
    h=hashlib.sha256();
    with open(path,'rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()
def norm_slash(p:str)->str: return p.replace('\\','/')
def join_repo_root(root:str, rel:str)->str:
    rel=rel.replace('/',os.sep).replace('\\',os.sep); return os.path.normpath(os.path.join(root,rel))

def _parse_hexish(v):
    if isinstance(v,int): return v
    if isinstance(v,str):
        s=v.strip().lower()
        if s.startswith('0x'): return int(s,16)
        return int(s,16) if all(c in '0123456789abcdef' for c in s) else int(s,10)
    raise ValueError('not int/str')

def check_unique_contract_versions(entries):
    seen=set(); dup=[]
    for e in entries:
      k=(e.get('contract_id'),e.get('version'))
      if k in seen: dup.append(k)
      seen.add(k)
    return (False,f"DUPLICATE_CONTRACT_VERSION: {dup}") if dup else (True,None)

def check_path_major_version(entries):
    errs=[]
    for e in entries:
      p=norm_slash(str(e.get('path',''))); v=str(e.get('version','')); m=re.search(r'/v(\d+)/',p)
      if not m: errs.append((e.get('contract_id'),'NO_VERSION_DIR')); continue
      if not v.startswith(m.group(1)+'.'): errs.append((e.get('contract_id'),v,f"DIR_v{m.group(1)}_MISMATCH"))
    return (False,f"VERSION_PATH_MISMATCH: {errs}") if errs else (True,None)

def check_registry_sorted(entries):
    exp=sorted(entries,key=lambda e:(str(e.get('contract_id','')),str(e.get('version',''))))
    return (False,'REGISTRY_NOT_SORTED') if entries!=exp else (True,None)

def validate_schema(index_obj:Any,schema_obj:Any):
    if jsonschema is not None:
      try: jsonschema.validate(instance=index_obj,schema=schema_obj); return True,None,'jsonschema'
      except Exception as e: return False,f'SCHEMA_FAIL: {e}','jsonschema'
    if not isinstance(schema_obj,(dict,list)): return False,'SCHEMA_FAIL: schema JSON must be object or array','minimal'
    if not isinstance(index_obj,dict): return False,'SCHEMA_FAIL: index.json must be object','minimal'
    entries=index_obj.get('entries')
    if not isinstance(entries,list): return False,'SCHEMA_FAIL: entries must be array','minimal'
    for i,e in enumerate(entries):
      if not isinstance(e,dict): return False,f'SCHEMA_FAIL: entries[{i}] must be object','minimal'
      miss=[k for k in REQUIRED_ENTRY_KEYS if k not in e]
      if miss: return False,f'SCHEMA_FAIL: entries[{i}] missing keys: {miss}','minimal'
      if e.get('category') not in CATEGORY_ENUM: return False,f'SCHEMA_FAIL: entries[{i}].category invalid','minimal'
      if not re.match(r'^\d+\.\d+(\.\d+)?$',str(e.get('version',''))): return False,f'SCHEMA_FAIL: entries[{i}].version invalid','minimal'
      if not re.match(r'^[0-9a-fA-F]{64}$',str(e.get('sha256',''))): return False,f'SCHEMA_FAIL: entries[{i}].sha256 invalid','minimal'
    return True,None,'minimal'

def validate_fixture_pack(manifest_path:str):
    try: m=load_json(manifest_path)
    except Exception as ex: return False,f'REGISTRY_ERROR: fixture manifest load failed: {ex}'
    files=m.get('files')
    if files is None: return False,'REGISTRY_ERROR: fixture manifest missing files[]'
    if not isinstance(files,list): return False,'REGISTRY_ERROR: fixture files must be array'
    root=os.path.dirname(manifest_path)
    for i,ent in enumerate(files):
      if not isinstance(ent,dict) or 'path' not in ent or 'sha256' not in ent:
        return False,f'REGISTRY_ERROR: fixture files[{i}] malformed'
      fp=os.path.normpath(os.path.join(root,str(ent['path']).replace('/',os.sep).replace('\\',os.sep)))
      if not os.path.exists(fp): return False,f"MISSING_FILE: fixture file missing {ent.get('path')}"
      got=sha256_file(fp).lower(); exp=str(ent.get('sha256','')).lower()
      if got!=exp: return False,f"FIXTURE_FILE_HASH_MISMATCH: {ent.get('path')}"
    return True,None

def validate_fw_handoff(repo_root:str, failures:list, fw_out:dict):
    fw_dir=os.path.join(repo_root,'out','release','0.1.0','fw_gate')
    handoff_path=os.path.join(fw_dir,'handoff.json')
    summary_path=os.path.join(fw_dir,'summary.json')
    bootlog_path=os.path.join(fw_dir,'boot.log')
    fw_out.update({'status':'FAIL','handoff_path':norm_slash(handoff_path),'summary_path':norm_slash(summary_path),'boot_log_path':norm_slash(bootlog_path),'platform_id':None,'fw_version':None,'handoff_contract_version':None,'failures':[]})

    def fail(code,detail):
        failures.append({'code':code,'detail':detail}); fw_out['failures'].append({'code':code,'detail':detail})

    if not os.path.exists(handoff_path): fail('FW_HANDOFF_MISSING',f'Missing {handoff_path}'); return False
    if not os.path.exists(summary_path): fail('FW_SUMMARY_MISSING',f'Missing {summary_path}'); return False
    if not os.path.exists(bootlog_path): fail('FW_BOOTLOG_MISSING',f'Missing {bootlog_path}'); return False

    try: handoff=load_json(handoff_path)
    except Exception as e: fail('FW_HANDOFF_SCHEMA_FAIL',f'handoff.json parse error: {e}'); return False
    try: summary=load_json(summary_path)
    except Exception as e: fail('FW_SUMMARY_NOT_PASS',f'summary.json parse error: {e}'); return False

    sum_status=None
    for k in ('status','result','fw_gate_status','FW_GATE_STATUS','overall'):
        if k in summary: sum_status=str(summary[k]).upper(); break
    if sum_status is None: fail('FW_SUMMARY_NOT_PASS','summary.json missing status field'); return False
    if sum_status not in ('PASS','OK','SUCCESS'): fail('FW_SUMMARY_NOT_PASS',f'summary status={sum_status}'); return False

    for k in ('platform_id','fw_version','handoff_contract_version','memory_map','boot_vector','timestamp_utc'):
        if k not in handoff: fail('FW_HANDOFF_SCHEMA_FAIL',f'handoff missing field: {k}'); return False

    platform_id=str(handoff.get('platform_id','')).strip()
    if not platform_id: fail('FW_HANDOFF_PLATFORM_UNKNOWN','platform_id empty'); return False

    hcver=str(handoff.get('handoff_contract_version','')).strip()
    m=re.match(r'^(\d+)\.',hcver)
    if not m: fail('FW_HANDOFF_SCHEMA_FAIL',f'handoff_contract_version not semver: {hcver}'); return False
    if m.group(1)!='1': fail('FW_HANDOFF_VERSION_MISMATCH',f'handoff_contract_version={hcver} expected 1.x'); return False

    try:
        bv=_parse_hexish(handoff.get('boot_vector'))
        if bv<=0: raise ValueError('boot_vector <= 0')
    except Exception as e:
        fail('FW_HANDOFF_BOOT_VECTOR_INVALID',f'boot_vector invalid: {e}'); return False

    mm=handoff.get('memory_map')
    if not isinstance(mm,list) or len(mm)<1: fail('FW_HANDOFF_MEMORY_INVALID','memory_map must be non-empty array'); return False
    try:
      for i,ent in enumerate(mm):
        if not isinstance(ent,dict): raise ValueError(f'memory_map[{i}] not object')
        base=_parse_hexish(ent.get('base')); size=_parse_hexish(ent.get('size'))
        if base<0 or size<=0: raise ValueError(f'memory_map[{i}] base/size invalid')
    except Exception as e:
      fail('FW_HANDOFF_MEMORY_INVALID',f'memory_map invalid: {e}'); return False

    fw_out.update({'status':'PASS','platform_id':platform_id,'fw_version':str(handoff.get('fw_version')),'handoff_contract_version':hcver,'failures':[]})
    return True


def validate_exit_registry(repo_root:str, failures:list):
    path=os.path.join(repo_root,'contracts','registry','integrity_exit_registry.json')
    if not os.path.exists(path):
        failures.append({'code':'REGISTRY_ERROR','detail':'integrity_exit_registry.json missing'})
        return False
    try:
        obj=load_json(path)
    except Exception as ex:
        failures.append({'code':'REGISTRY_ERROR','detail':f'integrity_exit_registry parse failed: {ex}'})
        return False
    sf=obj.get('slice_failures',{})
    rg=obj.get('release_gates',{})
    slice_codes=[]; gate_codes=[]
    for _,v in sf.items():
        if isinstance(v,list):
            slice_codes.extend([int(x) for x in v])
    for _,v in rg.items():
        gate_codes.append(int(v))
    all_codes=slice_codes+gate_codes
    if len(all_codes)!=len(set(all_codes)):
        failures.append({'code':'EXIT_CODE_COLLISION_DETECTED','detail':'duplicate exit codes detected'})
        return False
    if set(slice_codes).intersection(set(gate_codes)):
        failures.append({'code':'EXIT_CODE_COLLISION_DETECTED','detail':'slice exits overlap gate exits'})
        return False
    bad=[]
    # Slice negatives: legacy 19xx plus extended 30xx band only.
    for c in slice_codes:
        in_legacy_slice_band = 400 <= c <= 1999
        in_new_30xx = 3000 <= c <= 3999
        if not (in_legacy_slice_band or in_new_30xx):
            bad.append(c)
    # Release gates: 2xxx band only.
    for c in gate_codes:
        if c < 500 or c > 2999:
            bad.append(c)
    if bad:
        failures.append({'code':'EXIT_CODE_COLLISION_DETECTED','detail':f'exit out of enforced range: {sorted(set(bad))}'})
        return False
    return True

def validate_actions_registry(repo_root:str, failures:list):
    tool=os.path.join(repo_root,'tools','governance','validate_actions_registry.py')
    if not os.path.exists(tool):
        failures.append({'code':'HOTKEY_ACTIONS_REGISTRY_VALIDATION_FAILED','detail':'validate_actions_registry.py missing'})
        return False
    p=subprocess.run([sys.executable, tool], cwd=repo_root, capture_output=True, text=True)
    if p.returncode!=0:
        failures.append({'code':'HOTKEY_ACTIONS_REGISTRY_VALIDATION_FAILED','detail':(p.stdout+p.stderr).strip()[:500]})
        return False
    return True

def validate_shell_hotkeys(repo_root:str, failures:list):
    tool=os.path.join(repo_root,'tools','governance','validate_shell_hotkeys.py')
    if not os.path.exists(tool):
        failures.append({'code':'HOTKEYS_VALIDATION_FAILED','detail':'validate_shell_hotkeys.py missing'})
        return False
    p=subprocess.run([sys.executable, tool], cwd=repo_root, capture_output=True, text=True)
    if p.returncode!=0:
        failures.append({'code':'HOTKEYS_VALIDATION_FAILED','detail':(p.stdout+p.stderr).strip()[:500]})
        return False
    return True

def validate_parallel_cubed_sandbox_domains(repo_root:str, failures:list):
    tool=os.path.join(repo_root,'tools','runtime','parallel_cubed_sandbox_domain_integrity_flow.py')
    if not os.path.exists(tool):
        failures.append({'code':'PARALLEL_CUBED_SANDBOX_DOMAIN_VALIDATION_FAILED','detail':'parallel_cubed_sandbox_domain_integrity_flow.py missing'})
        return False
    p=subprocess.run([sys.executable, tool], cwd=repo_root, capture_output=True, text=True)
    if p.returncode!=0:
        detail=(p.stdout+p.stderr).strip()[:500] or f'validator exit={p.returncode}'
        failures.append({'code':'PARALLEL_CUBED_SANDBOX_DOMAIN_VALIDATION_FAILED','detail':detail})
        return False
    return True
def write_result(out_path:str,result:Dict[str,Any]):
    os.makedirs(os.path.dirname(out_path),exist_ok=True)
    tmp=out_path+'.tmp'
    with open(tmp,'w',encoding='utf-8') as f: json.dump(result,f,indent=2,sort_keys=True); f.write('\n')
    os.replace(tmp,out_path)

def main()->int:
    root=os.path.normpath(os.getcwd())
    idxp=os.path.join(root,'contracts','registry','index.json'); schp=os.path.join(root,'contracts','registry','index.schema.json'); outp=os.path.join(root,'out','contracts','registry_validation.json')
    r={'timestamp_utc':utc_now_iso(),'repo_root':norm_slash(root),'index_path':norm_slash(idxp),'schema_path':norm_slash(schp),'schema_validation_mode':None,'validation_status':'FAIL','exit_code':EXIT_REGISTRY_ERROR,'checked_entries':0,'failures':[],'entry_results':[],'fw_handoff':{}}
    try: idx=load_json(idxp); sch=load_json(schp)
    except Exception as e: r['failures'].append({'code':'REGISTRY_ERROR','detail':f'Load failed: {e}'}); write_result(outp,r); return EXIT_REGISTRY_ERROR
    ok,err,mode=validate_schema(idx,sch); r['schema_validation_mode']=mode
    if not ok: r['exit_code']=EXIT_SCHEMA_FAIL; r['failures'].append({'code':'SCHEMA_FAIL','detail':err}); write_result(outp,r); return EXIT_SCHEMA_FAIL
    entries=list(idx.get('entries',[])); r['checked_entries']=len(entries)
    for chk in (check_unique_contract_versions,check_path_major_version,check_registry_sorted):
      ok,err=chk(entries)
      if not ok and err: r['failures'].append({'code':err.split(':',1)[0].strip(),'detail':err})
    missing=False; hashmis=False; regerr=False
    for e in entries:
      cid=str(e.get('contract_id','')); cat=str(e.get('category','')); ver=str(e.get('version','')); rel=str(e.get('path','')); exp=str(e.get('sha256','')).lower(); abs=join_repo_root(root,rel)
      er={'contract_id':cid,'category':cat,'version':ver,'path':norm_slash(rel),'abs_path':norm_slash(abs),'exists':False,'sha256_expected':exp,'sha256_actual':None,'status':'FAIL','failure':None}
      if not os.path.exists(abs): missing=True; er['failure']={'code':'MISSING_FILE','detail':'Path does not exist'}; r['entry_results'].append(er); continue
      er['exists']=True
      if cat=='fixture' and '/fixtures/' in norm_slash(abs):
        okf,errf=validate_fixture_pack(abs)
        if not okf:
          c=str(errf).split(':',1)[0]
          if c=='MISSING_FILE': missing=True
          elif c=='FIXTURE_FILE_HASH_MISMATCH': hashmis=True
          else: regerr=True
          er['failure']={'code':c,'detail':str(errf)}; r['entry_results'].append(er); continue
      try:
        got=sha256_file(abs).lower(); er['sha256_actual']=got
        if exp and exp!=got: hashmis=True; er['failure']={'code':'HASH_MISMATCH','detail':'sha256 mismatch'}
        else: er['status']='PASS'
      except Exception as ex:
        regerr=True; er['failure']={'code':'REGISTRY_ERROR','detail':f'Hash read failed: {ex}'}
      r['entry_results'].append(er)

    fw_ok=validate_fw_handoff(root,r['failures'],r['fw_handoff'])
    exits_ok=validate_exit_registry(root,r['failures'])
    actions_ok=validate_actions_registry(root,r['failures'])
    hotkeys_ok=validate_shell_hotkeys(root,r['failures'])
    parallel_cubed_ok=validate_parallel_cubed_sandbox_domains(root,r['failures'])
    fw_fail=not fw_ok
    actions_fail=not actions_ok
    hotkeys_fail=not hotkeys_ok
    parallel_cubed_fail=not parallel_cubed_ok

    if missing: r['exit_code']=EXIT_MISSING_FILE
    elif hashmis: r['exit_code']=EXIT_HASH_MISMATCH
    elif regerr or len(r['failures'])>0 or fw_fail or (not exits_ok) or hotkeys_fail or actions_fail or parallel_cubed_fail: r['exit_code']=EXIT_REGISTRY_ERROR
    else: r['exit_code']=EXIT_PASS
    r['validation_status']='PASS' if r['exit_code']==EXIT_PASS else 'FAIL'; write_result(outp,r); return int(r['exit_code'])

if __name__=='__main__': raise SystemExit(main())









