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
import json, sys
from pathlib import Path
from datetime import datetime, timezone
BUS = Path(axion_path_str('runtime', 'shell_ui', 'event_bus'))
if str(BUS) not in sys.path: sys.path.append(str(BUS))
from event_bus import publish
STATE_PATH = Path(axion_path_str('config', 'ACCESSIBILITY_STATE_V1.json'))

def _now(): return datetime.now(timezone.utc).isoformat()
def _load(): return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))
def _save(s): STATE_PATH.write_text(json.dumps(s, indent=2) + "\n", encoding='utf-8')

def snapshot(corr='corr_acc_snap_001'):
    s=_load(); out={'ts':_now(),'corr':corr,**s,'sections':['Vision','Hearing','Input','Motion','Narrator','Captions']}; publish('shell.accessibility.refreshed',{'ok':True},corr=corr,source='accessibility_host'); return out

def set_value(section,key,val,corr='corr_acc_set_001'):
    s=_load()
    if section not in s or key not in s[section]: return {'ok':False,'code':'ACC_KEY_UNKNOWN'}
    s[section][key]=val; _save(s)
    publish('shell.accessibility.changed',{'section':section,'key':key,'value':val},corr=corr,source='accessibility_host')
    return {'ok':True,'code':'ACC_SET_OK'}

if __name__=='__main__': print(json.dumps(snapshot(),indent=2))

