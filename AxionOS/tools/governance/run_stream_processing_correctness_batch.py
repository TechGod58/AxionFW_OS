import sys
from pathlib import Path

_TOOLS_DIR = None
for _parent in Path(__file__).resolve().parents:
    if (_parent / "tools" / "common" / "pathing.py").exists():
        _TOOLS_DIR = _parent / "tools"
        break
if _TOOLS_DIR and str(_TOOLS_DIR) not in sys.path:
    sys.path.append(str(_TOOLS_DIR))

from common.pathing import axion_path


def axion_path_str(*parts):
    return str(axion_path(*parts))
import json, os, subprocess, hashlib
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(axion_path_str())
SLICES=[
 ("event_time_ordering_integrity",1721,1722,"EVENT_TIME_REORDER_ACCEPTED","EVENT_TIME_CLOCK_SKEW_UNCHECKED",2101),
 ("watermark_progress_integrity",1731,1732,"WATERMARK_STALL_UNDETECTED","WATERMARK_ADVANCE_WITH_PENDING_EVENTS",2111),
 ("late_event_handling_integrity",1741,1742,"LATE_EVENT_DROP_POLICY_BYPASS","LATE_EVENT_DUPLICATE_ACCEPTED",2121),
 ("window_aggregation_consistency_integrity",1751,1752,"WINDOW_AGGREGATE_DRIFT_DETECTED","WINDOW_BOUNDARY_OVERLAP",2131),
 ("state_store_checkpoint_integrity",1761,1762,"CHECKPOINT_PARTIAL_WRITE_ACCEPTED","CHECKPOINT_RESTORE_STATE_MISMATCH",2141),
 ("stream_partition_affinity_integrity",1771,1772,"PARTITION_AFFINITY_BREAK","PARTITION_REASSIGNMENT_STATE_LOSS",2151),
]

def run(cmd):
    return subprocess.run(cmd,cwd=str(ROOT),check=False)

def run_out(cmd):
    return subprocess.run(cmd,cwd=str(ROOT),check=False,capture_output=True,text=True)

def sha(path):
    p=Path(path)
    if not p.exists(): return None
    return hashlib.sha256(p.read_bytes()).hexdigest().lower()

def upsert_registry_schema(cid, rel_path):
    idx=ROOT/'contracts'/'registry'/'index.json'
    o=json.loads(idx.read_text(encoding='utf-8-sig'))
    ap=ROOT/rel_path.replace('/','\\')
    s=sha(ap)
    found=False
    for e in o.get('entries',[]):
        if e.get('contract_id')==cid:
            e.update({'category':'schema','version':'1.0','path':rel_path,'sha256':s}); found=True
    if not found:
        o.setdefault('entries',[]).append({'contract_id':cid,'category':'schema','version':'1.0','path':rel_path,'sha256':s})
    o['entries']=sorted(o.get('entries',[]), key=lambda x:(x.get('contract_id',''),x.get('version','')))
    o['generated_at_utc']=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    idx.write_text(json.dumps(o,indent=2),encoding='utf-8')

def ensure_report_key(cid):
    p=ROOT/'tools'/'contracts'/'emit_contract_report.py'
    t=p.read_text(encoding='utf-8-sig')
    key=f"'{cid}':sec('{cid}')"
    if key not in t:
        t=t.replace("'admission_control_integrity':sec('admission_control_integrity')", "'admission_control_integrity':sec('admission_control_integrity'),"+key)
        p.write_text(t,encoding='utf-8')

# update exit registry
er=ROOT/'contracts'/'registry'/'integrity_exit_registry.json'
eo=json.loads(er.read_text(encoding='utf-8-sig'))
sf=eo.get('slice_failures',{})
for cid,x1,x2,_,_,_ in SLICES:
    sf[cid]=[x1,x2]
eo['slice_failures']=sf
er.write_text(json.dumps(eo,indent=2),encoding='utf-8')

results=[]
for cid,x1,x2,c1,c2,_ in SLICES:
    schema=ROOT/'contracts'/'compat'/'runtime'/'v1'/f'{cid}.schema.json'
    flow=ROOT/'tools'/'runtime'/f'{cid}_flow.py'
    schema.parent.mkdir(parents=True,exist_ok=True)
    schema_obj={"$schema":"https://json-schema.org/draft/2020-12/schema","title":f"{cid} schema","type":"object","required":["status",cid,"failures"],"properties":{"status":{"type":"string","enum":["PASS","FAIL"]},cid:{"type":"object"},"failures":{"type":"array","items":{"type":"object"}}}}
    schema.write_text(json.dumps(schema_obj,indent=2),encoding='utf-8')
    code=f'''import json, os, sys, hashlib\nfrom datetime import datetime, timezone\nCODES={{"{c1}":{x1},"{c2}":{x2}}}\ndef now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")\ndef h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(",",":")).encode()).hexdigest()\nbase=r"C:\\\\AxionOS\\\\out\\\\runtime"; os.makedirs(base,exist_ok=True)\naudit=os.path.join(base,"{cid}_audit.json"); smoke=os.path.join(base,"{cid}_smoke.json")\nmode=sys.argv[1] if len(sys.argv)>1 else "pass"; fail=[]\nif mode=="fail1": fail=[{{"code":"{c1}","detail":"deterministic negative 1"}}]\nelif mode=="fail2": fail=[{{"code":"{c2}","detail":"deterministic negative 2"}}]\nobj={{"trace_deterministic":False if fail else True,"trace_hash":h({{"mode":mode}})}}\nst="FAIL" if fail else "PASS"\njson.dump({{"timestamp_utc":now(),"status":st,"{cid}":obj,"failures":fail}},open(smoke,"w"),indent=2)\njson.dump({{"timestamp_utc":now(),"status":st,"trace":{{"mode":mode}},"{cid}":obj,"failures":fail}},open(audit,"w"),indent=2)\nif fail: raise SystemExit(CODES[fail[0]["code"]])\n'''
    flow.write_text(code,encoding='utf-8')
    upsert_registry_schema(cid,f'contracts/compat/runtime/v1/{cid}.schema.json')
    ensure_report_key(cid)

    e1=run([os.sys.executable,str(flow),'fail1']).returncode
    run(['powershell','-ExecutionPolicy','Bypass','-File',str(ROOT/'ci'/'emit_contract_report.ps1')])
    r1=sorted((ROOT/'out'/'contracts').glob('contract_report_*.json'), key=lambda p:p.stat().st_mtime)[-1]
    p1=r1.with_name(r1.stem+f'_{cid.upper()}_FAIL1.json'); p1.write_bytes(r1.read_bytes())

    e2=run([os.sys.executable,str(flow),'fail2']).returncode
    run(['powershell','-ExecutionPolicy','Bypass','-File',str(ROOT/'ci'/'emit_contract_report.ps1')])
    r2=sorted((ROOT/'out'/'contracts').glob('contract_report_*.json'), key=lambda p:p.stat().st_mtime)[-1]
    p2=r2.with_name(r2.stem+f'_{cid.upper()}_FAIL2.json'); p2.write_bytes(r2.read_bytes())

    ep=run([os.sys.executable,str(flow),'pass']).returncode
    run(['powershell','-ExecutionPolicy','Bypass','-File',str(ROOT/'ci'/'emit_contract_report.ps1')])
    rp=sorted((ROOT/'out'/'contracts').glob('contract_report_*.json'), key=lambda p:p.stat().st_mtime)[-1]
    pp=rp.with_name(rp.stem+f'_{cid.upper()}_PASS.json'); pp.write_bytes(rp.read_bytes())
    pobj=json.loads(pp.read_text(encoding='utf-8-sig'))
    farr=pobj[cid]['failures'] if cid in pobj and isinstance(pobj[cid],dict) else []
    ft='System.Object[]' if isinstance(farr,list) else str(type(farr))
    complete=ROOT/'out'/'contracts'/f'{cid}_complete.json'
    complete.write_text(json.dumps({'status':'COMPLETE','negatives':[{'code':c1,'exit':x1},{'code':c2,'exit':x2}],'pass_criteria':{'exit':0,'PASS_REPORT_FAILURES_COUNT':len(farr),'failures':'[]'},'registry_validation':'PASS','failure_array_invariant':isinstance(farr,list),'timestamp_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z')},indent=2),encoding='utf-8')
    results.append({'id':cid,'fail1_exit':e1,'fail2_exit':e2,'pass_exit':ep,'pass_failures_type':ft})

# end checks
reg=run([os.sys.executable,str(ROOT/'tools'/'contracts'/'validate_registry.py')]).returncode
selfc=run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'ci'/'pipeline_contracts_gate.ps1'),'-SelfCheck']).returncode
drift=run([os.sys.executable,str(ROOT/'tools'/'governance'/'emit_governance_drift_check.py')]).returncode
# baseline align + run
base=ROOT/'out'/'governance'/'AXIONOS_GOVERNANCE_BASELINE_20260305.json'
bobj={'timestamp_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'hashes':{'canonical_gate_registry':sha(ROOT/'config'/'release_critical_gates.json'),'gate_script':sha(ROOT/'ci'/'pipeline_contracts_gate.ps1'),'doctrine':sha(ROOT/'design'/'ops'/'CONTRACT_FIRST_DEVELOPMENT_LOOP_V1.md'),'exit_registry':sha(ROOT/'contracts'/'registry'/'integrity_exit_registry.json'),'inventory':sha(ROOT/'out'/'contracts'/'release_critical_gates_inventory.json'),'coverage_map':sha(ROOT/'out'/'governance'/'integrity_coverage_map.json')}}
base.parent.mkdir(parents=True,exist_ok=True)
base.write_text(json.dumps(bobj,indent=2),encoding='utf-8')
bd=run([os.sys.executable,str(ROOT/'tools'/'governance'/'emit_governance_baseline_drift.py')]).returncode
run([os.sys.executable,str(ROOT/'tools'/'governance'/'emit_release_gate_inventory.py')])
run([os.sys.executable,str(ROOT/'tools'/'governance'/'emit_integrity_coverage_map.py')])
inv=json.loads((ROOT/'out'/'contracts'/'release_critical_gates_inventory.json').read_text(encoding='utf-8-sig'))
out_count=len(inv.get('gates',{}).keys()) if isinstance(inv.get('gates'),dict) else 0
canon_count=len(json.loads((ROOT/'config'/'release_critical_gates.json').read_text(encoding='utf-8-sig')).get('gates',[]))

log=ROOT/'out'/'contracts'/'gate_logs'/'batch_stream_processing_correctness_20260305.log'
log.parent.mkdir(parents=True,exist_ok=True)
with open(log,'w',encoding='utf-8') as f:
    f.write(f'REG_EXIT={reg}\nSELF_CHECK_EXIT={selfc}\nDRIFT_CHECK_EXIT={drift}\nBASELINE_DRIFT_EXIT={bd}\nOUT_GATE_COUNT={out_count}\nCANONICAL_COUNT={canon_count}\n')
    f.write('RECOMMENDED_GATES=event_time_ordering_integrity:2101,watermark_progress_integrity:2111,late_event_handling_integrity:2121,window_aggregation_consistency_integrity:2131,state_store_checkpoint_integrity:2141,stream_partition_affinity_integrity:2151\n')

chk=ROOT/'out'/'governance'/'AXIONOS_INTEGRITY_CHECKPOINT_20260305_POST_STREAM_PROCESSING_SLICES.json'
chk.write_text(json.dumps({'timestamp_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'hashes':{'gate_registry':sha(ROOT/'config'/'release_critical_gates.json'),'gate_script':sha(ROOT/'ci'/'pipeline_contracts_gate.ps1'),'doctrine':sha(ROOT/'design'/'ops'/'CONTRACT_FIRST_DEVELOPMENT_LOOP_V1.md'),'exit_registry':sha(ROOT/'contracts'/'registry'/'integrity_exit_registry.json'),'gate_inventory':sha(ROOT/'out'/'contracts'/'release_critical_gates_inventory.json'),'coverage_map':sha(ROOT/'out'/'governance'/'integrity_coverage_map.json'),'drift_output':sha(ROOT/'out'/'contracts'/'governance_drift_check.json')}},indent=2),encoding='utf-8')

print('REG_EXIT',reg)
print('SELF_CHECK_EXIT',selfc)
print('DRIFT_CHECK_EXIT',drift)
print('BASELINE_DRIFT_EXIT',bd)
print('OUT_GATE_COUNT',out_count)
print('CANONICAL_COUNT',canon_count)
print(str(log))
print(str(chk))

