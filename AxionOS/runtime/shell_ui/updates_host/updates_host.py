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
STATE_PATH = Path(axion_path_str('config', 'UPDATES_STATE_V1.json'))

def _now(): return datetime.now(timezone.utc).isoformat()
def _load(): return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))
def _save(s): STATE_PATH.write_text(json.dumps(s, indent=2), encoding='utf-8')

def snapshot(corr='corr_upd_snap_001'):
    s=_load(); out={'ts':_now(),'corr':corr,**s}; publish('shell.updates.refreshed',{'ok':True},corr=corr,source='updates_host'); return out

def check(corr='corr_upd_check_001'):
    s=_load(); s['last_check']=_now(); _save(s); publish('shell.updates.check',{'status':'ok'},corr=corr,source='updates_host'); return {'ok':True,'code':'UPDATES_CHECK_OK'}

def set_defer(days:int,corr='corr_upd_defer_001'):
    s=_load(); s['defer_days']=max(0,int(days)); _save(s); publish('shell.updates.defer.changed',{'days':s['defer_days']},corr=corr,source='updates_host'); return {'ok':True,'code':'UPDATES_DEFER_SET_OK'}

def install(update_id:str,corr='corr_upd_install_001'):
    s=_load(); s['last_install']=_now(); s['status']='up_to_date'; _save(s); publish('shell.updates.install',{'update_id':update_id},corr=corr,source='updates_host'); return {'ok':True,'code':'UPDATES_INSTALL_OK','update_id':update_id}

if __name__=='__main__': print(json.dumps(snapshot(),indent=2))

