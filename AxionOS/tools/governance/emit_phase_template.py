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
import argparse, json
from pathlib import Path

ROOT=Path(axion_path_str())

PHASES=['B1','B2','B3','B4','B5']


def chunk(lst,n):
    for i in range(0,len(lst),n):
        yield lst[i:i+n]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--plan', required=True)
    ap.add_argument('--out', default=axion_path_str('out', 'governance', 'rails'))
    args=ap.parse_args()
    plan=json.loads(Path(args.plan).read_text(encoding='utf-8-sig'))
    items=plan.get('promotions',[])
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    workers=ROOT/'tools'/'governance'/'workers'; workers.mkdir(parents=True,exist_ok=True)
    phases=[]
    for idx,group in enumerate(chunk(items,5),start=1):
        pid=f'B{idx}'
        phases.append({'phase':pid,'count':len(group),'items':group})
        w=workers/f'promote_stream_processing_{pid}.py'
        code=[
            'import json, subprocess','from pathlib import Path','from datetime import datetime, timezone',
            f"PHASE='{pid}'","ROOT=Path(__file__).resolve().parents[3]","OUT=ROOT/'out'/'governance'/'rails'",'OUT.mkdir(parents=True,exist_ok=True)',
            f'ITEMS={json.dumps(group)}',
            "(OUT/f'phase_{PHASE}_start.txt').write_text(datetime.now(timezone.utc).isoformat()+'Z',encoding='utf-8')",
            "print(f'PHASE_START {PHASE} {len(ITEMS)}')",
            "# placeholder promotion loop (actual promotion handled by main orchestrator)",
            "(OUT/f'phase_{PHASE}_done.txt').write_text(datetime.now(timezone.utc).isoformat()+'Z',encoding='utf-8')",
            "json.dump({'phase':PHASE,'exit':0,'count':len(ITEMS)},open(OUT/f'phase_{PHASE}_results.json','w',encoding='utf-8'),indent=2)",
            "print(f'PHASE_DONE {PHASE} EXIT=0')"
        ]
        w.write_text('\n'.join(code)+'\n',encoding='utf-8')
    plan_out=out/'phase_plan.json'
    plan_out.write_text(json.dumps({'phases':phases},indent=2),encoding='utf-8')
    print(plan_out)

if __name__=='__main__':
    main()

