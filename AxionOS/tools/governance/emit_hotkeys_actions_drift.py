#!/usr/bin/env python3
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

ROOT=Path(axion_path_str())
HOTKEYS=ROOT/'config'/'shell_hotkeys.json'
ACTIONS=ROOT/'config'/'actions_registry.json'
OUT=ROOT/'out'/'ui'/'hotkeys_actions_drift.json'
from hotkey_normalize import normalize_chord

def main():
    h=json.loads(HOTKEYS.read_text(encoding='utf-8-sig'))
    a=json.loads(ACTIONS.read_text(encoding='utf-8-sig'))
    action_ids={x.get('action_id') for x in a.get('actions',[])}
    dangling=[]; unused=set(action_ids); dup=[]; badc=[]; badctx=[]
    seen={}
    allow=set(h.get('context_allowlist',[]))
    for row in h.get('hotkeys',[]):
        aid=row.get('action_id'); ctx=row.get('context','global'); ch=row.get('chord','')
        if aid not in action_ids: dangling.append({'action_id':aid,'context':ctx,'chord':ch})
        else: unused.discard(aid)
        try: n=normalize_chord(ch)
        except Exception: badc.append({'action_id':aid,'chord':ch}); continue
        if ctx not in allow: badctx.append({'action_id':aid,'context':ctx})
        if row.get('enabled',True):
            k=(ctx,n)
            if k in seen: dup.append({'context':ctx,'chord':n,'actions':[seen[k],aid]})
            else: seen[k]=aid
    out={'dangling_hotkey_actions':dangling,'unused_actions':sorted(unused),'duplicate_chords':dup,'invalid_chords':badc,'invalid_contexts':badctx}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(str(OUT))
    return 0

if __name__=='__main__':
    raise SystemExit(main())

