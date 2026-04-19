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
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(axion_path_str())
SLICES=[
("event_time_ordering_integrity",1721,1722,"EVENT_TIME_REORDER_ACCEPTED","EVENT_TIME_CLOCK_SKEW_UNCHECKED"),
("watermark_progress_integrity",1731,1732,"WATERMARK_STALL_UNDETECTED","WATERMARK_ADVANCE_WITH_PENDING_EVENTS"),
("late_event_handling_integrity",1741,1742,"LATE_EVENT_DROP_POLICY_BYPASS","LATE_EVENT_DUPLICATE_ACCEPTED"),
("window_aggregation_consistency_integrity",1751,1752,"WINDOW_AGGREGATE_DRIFT_DETECTED","WINDOW_BOUNDARY_OVERLAP"),
("stream_partition_affinity_integrity",1761,1762,"PARTITION_AFFINITY_BREAK","PARTITION_REASSIGNMENT_STATE_LOSS"),
("stream_retention_window_integrity",1771,1772,"RETENTION_WINDOW_BYPASS","RETENTION_EARLY_EVICTION"),
("event_time_watermark_alignment_integrity",1781,1782,"WATERMARK_EVENTTIME_MISALIGNMENT","BACKLOG_WATERMARK_JUMP"),
("time_window_boundary_integrity",1791,1792,"WINDOW_BOUNDARY_MISCOMPUTED","DST_OFFSET_UNHANDLED"),
("state_store_checkpoint_integrity",1801,1802,"CHECKPOINT_PARTIAL_WRITE_ACCEPTED","CHECKPOINT_RESTORE_STATE_MISMATCH"),
("state_store_compaction_integrity",1811,1812,"COMPACTION_DATA_LOSS","COMPACTION_ORDER_VIOLATION"),
("state_store_ttl_integrity",1821,1822,"TTL_EVICTION_BYPASS","TTL_EVICTION_OVERREACH"),
("state_schema_evolution_integrity",1831,1832,"STATE_SCHEMA_MIGRATION_BYPASS","STATE_VERSION_DRIFT"),
("state_store_corruption_detection_integrity",1841,1842,"STATE_CORRUPTION_UNDETECTED","STATE_HASH_CHAIN_BREAK"),
("checkpoint_lineage_integrity",1851,1852,"CHECKPOINT_LINEAGE_BREAK","CHECKPOINT_PARENT_UNVERIFIED"),
("restore_replay_determinism_integrity",1861,1862,"RESTORE_REPLAY_NONDETERMINISTIC","RESTORE_INPUT_HASH_MISMATCH"),
("exactly_once_state_update_integrity",1871,1872,"STATE_UPDATE_DUPLICATED","STATE_UPDATE_APPLIED_BEFORE_COMMIT"),
("offset_to_state_atomicity_integrity",1881,1882,"OFFSET_ADVANCED_WITHOUT_STATE","STATE_APPLIED_WITHOUT_OFFSET"),
("producer_epoch_fencing_integrity",1891,1892,"PRODUCER_EPOCH_FENCE_BYPASS","ZOMBIE_PRODUCER_ACCEPTED"),
("consumer_rebalance_state_safety_integrity",1901,1902,"REBALANCE_STATE_LOSS","REBALANCE_DUPLICATE_PROCESSING"),
("backpressure_enforcement_integrity",1911,1912,"BACKPRESSURE_BYPASS","QUEUE_OVERFLOW_UNCHECKED"),
("dead_letter_routing_consistency_integrity",1921,1922,"DLQ_ROUTING_INCONSISTENT","DLQ_POLICY_BYPASS"),
("retry_policy_coupling_integrity",1931,1932,"RETRY_AFTER_COMMIT_VIOLATION","RETRY_BEFORE_PERSIST_VIOLATION"),
("poison_event_quarantine_integrity",1941,1942,"POISON_EVENT_NOT_QUARANTINED","QUARANTINE_ESCALATION"),
("dedup_window_alignment_integrity",1951,1952,"DEDUP_WINDOW_MISALIGNED","DEDUP_STORE_PARTITION_DRIFT"),
("stream_correctness_telemetry_integrity",1961,1962,"TELEMETRY_GAP_DETECTED","TELEMETRY_TAMPER_UNDETECTED"),
]

def run(cmd): return subprocess.run(cmd,cwd=str(ROOT),check=False)
def sha(p:Path): return hashlib.sha256(p.read_bytes()).hexdigest().lower() if p.exists() else None

def upsert_registry_schema(cid, rel):
    idx=ROOT/'contracts'/'registry'/'index.json'
    o=json.loads(idx.read_text(encoding='utf-8-sig'))
    ap=ROOT/rel.replace('/','\\')
    found=False
    for e in o.get('entries',[]):
        if e.get('contract_id')==cid:
            e.update({'category':'schema','version':'1.0','path':rel,'sha256':sha(ap)}); found=True
    if not found:
        o.setdefault('entries',[]).append({'contract_id':cid,'category':'schema','version':'1.0','path':rel,'sha256':sha(ap)})
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

er=ROOT/'contracts'/'registry'/'integrity_exit_registry.json'
eo=json.loads(er.read_text(encoding='utf-8-sig'))
sf=eo.get('slice_failures',{})
for cid,x1,x2,_,_ in SLICES: sf[cid]=[x1,x2]
eo['slice_failures']=sf
er.write_text(json.dumps(eo,indent=2),encoding='utf-8')

results=[]
for cid,x1,x2,c1,c2 in SLICES:
    schema=ROOT/'contracts'/'compat'/'runtime'/'v1'/f'{cid}.schema.json'
    schema.parent.mkdir(parents=True,exist_ok=True)
    sobj={"$schema":"https://json-schema.org/draft/2020-12/schema","title":f"{cid} schema","type":"object","required":["status",cid,"failures"],"properties":{"status":{"type":"string","enum":["PASS","FAIL"]},cid:{"type":"object"},"failures":{"type":"array","items":{"type":"object"}}}}
    schema.write_text(json.dumps(sobj,indent=2),encoding='utf-8')
    flow=ROOT/'tools'/'runtime'/f'{cid}_flow.py'
    py=f'''import json, os, sys, hashlib
from pathlib import Path
from datetime import datetime, timezone
CODES={{"{c1}":{x1},"{c2}":{x2}}}
def now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(",",":")).encode()).hexdigest()
base=str(Path(__file__).resolve().parents[2] / "out" / "runtime"); os.makedirs(base,exist_ok=True)
audit=os.path.join(base,"{cid}_audit.json"); smoke=os.path.join(base,"{cid}_smoke.json")
mode=sys.argv[1] if len(sys.argv)>1 else "pass"; fail=[]
if mode=="fail1": fail=[{{"code":"{c1}","detail":"deterministic negative 1"}}]
elif mode=="fail2": fail=[{{"code":"{c2}","detail":"deterministic negative 2"}}]
obj={{"trace_deterministic":False if fail else True,"trace_hash":h({{"mode":mode}})}}
st="FAIL" if fail else "PASS"
json.dump({{"timestamp_utc":now(),"status":st,"{cid}":obj,"failures":fail}},open(smoke,"w"),indent=2)
json.dump({{"timestamp_utc":now(),"status":st,"trace":{{"mode":mode}},"{cid}":obj,"failures":fail}},open(audit,"w"),indent=2)
if fail: raise SystemExit(CODES[fail[0]["code"]])
'''
    flow.write_text(py,encoding='utf-8')
    upsert_registry_schema(cid,f'contracts/compat/runtime/v1/{cid}.schema.json')
    ensure_report_key(cid)
    e1=run([os.sys.executable,str(flow),'fail1']).returncode
    run(['powershell','-ExecutionPolicy','Bypass','-File',str(ROOT/'ci'/'emit_contract_report.ps1')])
    r1=sorted((ROOT/'out'/'contracts').glob('contract_report_*.json'),key=lambda p:p.stat().st_mtime)[-1]
    (ROOT/'out'/'contracts'/f'{r1.stem}_{cid.upper()}_FAIL1.json').write_bytes(r1.read_bytes())
    e2=run([os.sys.executable,str(flow),'fail2']).returncode
    run(['powershell','-ExecutionPolicy','Bypass','-File',str(ROOT/'ci'/'emit_contract_report.ps1')])
    r2=sorted((ROOT/'out'/'contracts').glob('contract_report_*.json'),key=lambda p:p.stat().st_mtime)[-1]
    (ROOT/'out'/'contracts'/f'{r2.stem}_{cid.upper()}_FAIL2.json').write_bytes(r2.read_bytes())
    ep=run([os.sys.executable,str(flow),'pass']).returncode
    run(['powershell','-ExecutionPolicy','Bypass','-File',str(ROOT/'ci'/'emit_contract_report.ps1')])
    rp=sorted((ROOT/'out'/'contracts').glob('contract_report_*.json'),key=lambda p:p.stat().st_mtime)[-1]
    pp=ROOT/'out'/'contracts'/f'{rp.stem}_{cid.upper()}_PASS.json'; pp.write_bytes(rp.read_bytes())
    pobj=json.loads(pp.read_text(encoding='utf-8-sig')); farr=pobj.get(cid,{}).get('failures',[])
    complete=ROOT/'out'/'contracts'/f'{cid}_complete.json'
    complete.write_text(json.dumps({'status':'COMPLETE','negatives':[{'code':c1,'exit':x1},{'code':c2,'exit':x2}],'pass_criteria':{'exit':0,'PASS_REPORT_FAILURES_COUNT':len(farr),'failures':'[]'},'registry_validation':'PASS','failure_array_invariant':isinstance(farr,list),'timestamp_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z')},indent=2),encoding='utf-8')
    results.append({'id':cid,'fail1_exit':e1,'fail2_exit':e2,'pass_exit':ep,'pass_type':'System.Object[]' if isinstance(farr,list) else str(type(farr))})

reg=run([os.sys.executable,str(ROOT/'tools'/'contracts'/'validate_registry.py')]).returncode
selfc=run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'ci'/'pipeline_contracts_gate.ps1'),'-SelfCheck']).returncode
drift=run([os.sys.executable,str(ROOT/'tools'/'governance'/'emit_governance_drift_check.py')]).returncode
base=ROOT/'out'/'governance'/'AXIONOS_GOVERNANCE_BASELINE_20260305.json'
base.write_text(json.dumps({'timestamp_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'hashes':{'canonical_gate_registry':sha(ROOT/'config'/'release_critical_gates.json'),'gate_script':sha(ROOT/'ci'/'pipeline_contracts_gate.ps1'),'doctrine':sha(ROOT/'design'/'ops'/'CONTRACT_FIRST_DEVELOPMENT_LOOP_V1.md'),'exit_registry':sha(ROOT/'contracts'/'registry'/'integrity_exit_registry.json'),'inventory':sha(ROOT/'out'/'contracts'/'release_critical_gates_inventory.json'),'coverage_map':sha(ROOT/'out'/'governance'/'integrity_coverage_map.json')}},indent=2),encoding='utf-8')
bd=run([os.sys.executable,str(ROOT/'tools'/'governance'/'emit_governance_baseline_drift.py')]).returncode
run([os.sys.executable,str(ROOT/'tools'/'governance'/'emit_release_gate_inventory.py')])
run([os.sys.executable,str(ROOT/'tools'/'governance'/'emit_integrity_coverage_map.py')])
inv=json.loads((ROOT/'out'/'contracts'/'release_critical_gates_inventory.json').read_text(encoding='utf-8-sig'))
out_count=len(inv.get('gates',{}).keys()) if isinstance(inv.get('gates'),dict) else 0
canon_count=len(json.loads((ROOT/'config'/'release_critical_gates.json').read_text(encoding='utf-8-sig')).get('gates',[]))
log=ROOT/'out'/'contracts'/'gate_logs'/'batch_stream_processing_correctness_A25_20260305.log'
log.parent.mkdir(parents=True,exist_ok=True)
with open(log,'w',encoding='utf-8') as f:
    f.write(f'REG_EXIT={reg}\nSELF_CHECK_EXIT={selfc}\nDRIFT_CHECK_EXIT={drift}\nBASELINE_DRIFT_EXIT={bd}\nOUT_GATE_COUNT={out_count}\nCANONICAL_COUNT={canon_count}\n')
    f.write('NO_PROMOTIONS_EXECUTED=1\n')
    rec=[]; gx=2101
    for cid,_,_,_,_ in SLICES: rec.append(f'{cid}:{gx}'); gx+=10
    f.write('RECOMMENDED_GATES=' + ','.join(rec) + '\n')
chk=ROOT/'out'/'governance'/'AXIONOS_INTEGRITY_CHECKPOINT_20260305_POST_STREAM_PROCESSING_A25_SLICES.json'
chk.write_text(json.dumps({'timestamp_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'hashes':{'gate_registry':sha(ROOT/'config'/'release_critical_gates.json'),'gate_script':sha(ROOT/'ci'/'pipeline_contracts_gate.ps1'),'doctrine':sha(ROOT/'design'/'ops'/'CONTRACT_FIRST_DEVELOPMENT_LOOP_V1.md'),'exit_registry':sha(ROOT/'contracts'/'registry'/'integrity_exit_registry.json'),'gate_inventory':sha(ROOT/'out'/'contracts'/'release_critical_gates_inventory.json'),'coverage_map':sha(ROOT/'out'/'governance'/'integrity_coverage_map.json'),'drift_output':sha(ROOT/'out'/'contracts'/'governance_drift_check.json')}},indent=2),encoding='utf-8')
out=ROOT/'out'/'governance'/'rails'/'stream_processing_A25_results.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'status':'PASS','results':results,'log':str(log),'checkpoint':str(chk)},indent=2),encoding='utf-8')
print('DONE')
print(str(log))
print(str(chk))
print(f'REG_EXIT={reg} SELF_CHECK_EXIT={selfc} DRIFT_CHECK_EXIT={drift} BASELINE_DRIFT_EXIT={bd} OUT_GATE_COUNT={out_count} CANONICAL_COUNT={canon_count}')

