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
import json
from pathlib import Path
ROOT = Path(axion_path_str('data', 'apps', 'notepad'))
ROOT.mkdir(parents=True, exist_ok=True)

def save_text(name: str, content: str):
    p = ROOT / f'{name}.txt'
    p.write_text(content, encoding='utf-8')
    return {'ok': True, 'code': 'NOTEPAD_SAVE_OK', 'file': str(p)}

def snapshot():
    return {'app': 'Notepad', 'count': len(list(ROOT.glob('*.txt')))}

if __name__ == '__main__':
    save_text('demo', 'hello')
    print(json.dumps(snapshot(), indent=2))

