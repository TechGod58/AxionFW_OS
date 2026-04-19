from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json
from datetime import datetime, timezone
import sys
from pathlib import Path
import os

sys.path.append(axion_path_str('runtime', 'shell_ui', 'orchestrator'))
from shell_orchestrator import handle_hotkey

def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

state_path=axion_path_str('out', 'runtime', 'boss_button_state.json')
if os.path.exists(state_path):
    os.remove(state_path)

out = {
    'timestamp_utc': now(),
    'step1': handle_hotkey('z', ctrl=True, alt=False, shift=False, current_view='/workspace', focus_context='non-input', ui_state={'pane':'editor'}, corr='corr_smoke_1'),
    'step2': handle_hotkey('z', ctrl=True, alt=False, shift=False, current_view='status_dashboard', focus_context='non-input', corr='corr_smoke_2'),
    'step3': handle_hotkey('z', ctrl=True, alt=False, shift=False, current_view='/editor', focus_context='input', corr='corr_smoke_3')
}
out['status'] = 'PASS' if out['step1'].get('code')=='BOSS_BUTTON_ON' and out['step2'].get('code')=='BOSS_BUTTON_OFF' and out['step3'].get('code')=='BOSS_BUTTON_SUPPRESSED_INPUT_FOCUS' else 'FAIL'
Path(axion_path_str('out', 'runtime')).mkdir(parents=True, exist_ok=True)
with open(axion_path_str('out', 'runtime', 'boss_button_smoke.json'),'w',encoding='utf-8') as f:
    json.dump(out,f,indent=2)
print(axion_path_str('out', 'runtime', 'boss_button_smoke.json'))
raise SystemExit(0 if out['status']=='PASS' else 1)

