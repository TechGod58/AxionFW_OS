from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib, importlib.util
from datetime import datetime, timezone

EXIT_REG=axion_path_str('contracts', 'registry', 'integrity_exit_registry.json')
with open(EXIT_REG,'r',encoding='utf-8-sig') as f:
    reg=json.load(f)
ex=reg.get('slice_failures',{}).get('boss_button_integrity',[400,401])
CODES={"BOSS_BUTTON_HOTKEY_UNREGISTERED":int(ex[0]),"BOSS_BUTTON_STATE_RESTORE_FAILED":int(ex[1])}

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()

spec=importlib.util.spec_from_file_location('shell_orchestrator', axion_path_str('runtime', 'shell_ui', 'orchestrator', 'shell_orchestrator.py'))
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit_p=os.path.join(base,'boss_button_integrity_audit.json'); smoke_p=os.path.join(base,'boss_button_integrity_smoke.json')
mode=sys.argv[1] if len(sys.argv)>1 else 'pass'
state_path=axion_path_str('out', 'runtime', 'boss_button_state.json')

fail=[]
if mode=='unregistered':
    if os.path.exists(state_path): os.remove(state_path)
    _=mod.handle_hotkey('z', ctrl=False, alt=False, current_view='/work', focus_context='non-input', corr='corr_boss_fail1')
    fail=[{'code':'BOSS_BUTTON_HOTKEY_UNREGISTERED','detail':'boss chord not matched/registered'}]
elif mode=='restore_failed':
    if os.path.exists(state_path): os.remove(state_path)
    mod.handle_hotkey('z', ctrl=True, alt=False, shift=False, current_view='/work', focus_context='non-input', corr='corr_boss_fail2_on')
    _=mod.handle_hotkey('z', ctrl=True, alt=False, shift=False, current_view='status_dashboard', focus_context='non-input', corr='corr_boss_fail2_off')
    fail=[{'code':'BOSS_BUTTON_STATE_RESTORE_FAILED','detail':'forced deterministic negative path'}]
else:
    # fresh-state path
    if os.path.exists(state_path): os.remove(state_path)
    on=mod.handle_hotkey('z', ctrl=True, alt=False, shift=False, current_view='/fresh', ui_state={'s':1}, focus_context='non-input', corr='corr_boss_pass_fresh_on')
    off=mod.handle_hotkey('z', ctrl=True, alt=False, shift=False, current_view='status_dashboard', focus_context='non-input', corr='corr_boss_pass_fresh_off')
    # seeded-state path
    seeded={'boss_active': True, 'safe_screen': 'status_dashboard', 'prior_view': '/seeded', 'prior_state': {'token': 'seed'}}
    with open(state_path,'w',encoding='utf-8') as f: json.dump(seeded,f)
    seeded_off=mod.handle_hotkey('z', ctrl=True, alt=False, shift=False, current_view='status_dashboard', focus_context='non-input', corr='corr_boss_pass_seeded_off')
    sup=mod.handle_hotkey('z', ctrl=True, alt=False, shift=False, current_view='/editor', focus_context='input', corr='corr_boss_pass3')
    if not (on.get('code')=='BOSS_BUTTON_ON' and off.get('code')=='BOSS_BUTTON_OFF' and off.get('view')=='/fresh' and seeded_off.get('code')=='BOSS_BUTTON_OFF' and seeded_off.get('view')=='/seeded' and sup.get('code')=='BOSS_BUTTON_SUPPRESSED_INPUT_FOCUS'):
        fail=[{'code':'BOSS_BUTTON_STATE_RESTORE_FAILED','detail':'pass criteria not met for fresh+seeded paths'}]

trace={'mode':mode}
obj={'toggle_works':False if fail else True,'restore_exact_state':False if fail else True,'trace_deterministic':False if fail else True,'trace_hash':h(trace)}
st='FAIL' if fail else 'PASS'
json.dump({'timestamp_utc':now(),'status':st,'boss_button':obj,'failures':fail},open(smoke_p,'w'),indent=2)
json.dump({'timestamp_utc':now(),'status':st,'trace':trace,'boss_button':obj,'failures':fail},open(audit_p,'w'),indent=2)
if fail: raise SystemExit(CODES[fail[0]['code']])

