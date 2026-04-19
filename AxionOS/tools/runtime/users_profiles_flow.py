from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

CODES = {
"USER_CREATE_INVALID":21,
"USER_ALREADY_EXISTS":22,
"PROFILE_CREATE_INVALID":23,
"PROFILE_ALREADY_EXISTS":24,
"PROFILE_SWITCH_INVALID":25,
"PROFILE_NOT_FOUND":26,
"PROFILE_DEFAULT_INVALID":27,
"PROFILE_AUDIT_FAIL":28,
}

PROFILE_SHELL_CFG = Path(axion_path_str('config', 'PROFILE_SHELL_FOLDERS_V1.json'))


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')


def write_json(p,obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p,'w',encoding='utf-8') as f:
        json.dump(obj,f,indent=2)


def load_profile_shell():
    return json.loads(PROFILE_SHELL_CFG.read_text(encoding='utf-8-sig'))


def resolve_profile_root_base(raw_base):
    text = str(raw_base or '').strip()
    if not text:
        return Path(axion_path_str('data', 'profiles'))
    pure = PureWindowsPath(text)
    if pure.is_absolute():
        parts = pure.parts
        if len(parts) >= 2 and parts[0].lower().startswith('c:') and parts[1].lower() == 'axionos':
            tail = list(parts[2:])
            return AXION_ROOT.joinpath(*tail) if tail else AXION_ROOT
        return Path(text)
    return AXION_ROOT.joinpath(*Path(text).parts)


def materialize_shell_folders(cfg, profile_id):
    order = cfg.get('folderOrder', [])
    folders = cfg.get('folders', {})
    profile_root_base = resolve_profile_root_base(cfg.get('profileRootBase'))
    profile_root = profile_root_base / profile_id
    profile_root.mkdir(parents=True, exist_ok=True)
    out = []
    for folder_id in order:
        folder = folders.get(folder_id)
        if not folder:
            continue
        root_path = profile_root / folder.get('pathSegment', folder_id)
        root_path.mkdir(parents=True, exist_ok=True)
        out.append({'folder_id': folder_id, **folder, 'rootPath': str(root_path)})
    return str(profile_root), out


def main():
    base=axion_path_str('out', 'runtime')
    audit_path=os.path.join(base,'users_profiles_audit.json')
    smoke_path=os.path.join(base,'users_profiles_smoke.json')
    mode='pass'
    if len(sys.argv)>1: mode=sys.argv[1]

    shell_cfg = load_profile_shell()
    workspace_links = list(shell_cfg.get('workspaceSurface', {}).get('defaultLinks', []))

    users=[]; profiles=[]; active=None; default=None; failures=[]; events=[]
    def fail(code,detail):
        failures.append({"code":code,"detail":detail})

    def create_user(user_id,name):
        if not user_id or not name:
            fail('USER_CREATE_INVALID','empty user'); return False
        if any(u['user_id']==user_id for u in users):
            fail('USER_ALREADY_EXISTS',user_id); return False
        users.append({"user_id":user_id,"display_name":name,"created_utc":now()}); events.append({"op":"create_user","user_id":user_id}); return True

    def create_profile(profile_id,user_id,name):
        if not profile_id or not user_id or not name:
            fail('PROFILE_CREATE_INVALID','bad profile'); return False
        if any(p['profile_id']==profile_id for p in profiles):
            fail('PROFILE_ALREADY_EXISTS',profile_id); return False
        if not any(u['user_id']==user_id for u in users):
            fail('PROFILE_CREATE_INVALID','user missing'); return False
        profile_root, shell_folders = materialize_shell_folders(shell_cfg, profile_id)
        profiles.append({
            "profile_id":profile_id,
            "user_id":user_id,
            "name":name,
            "created_utc":now(),
            "profile_root": profile_root,
            "workspace_surface": shell_cfg.get('workspaceSurface', {}),
            "save_policy": shell_cfg.get('savePolicy', {}),
            "shell_folders": shell_folders,
            "workspace_links": workspace_links
        })
        events.append({"op":"create_profile","profile_id":profile_id})
        return True

    def switch_profile(profile_id):
        nonlocal active
        if not profile_id: fail('PROFILE_SWITCH_INVALID','empty profile id'); return False
        if not any(p['profile_id']==profile_id for p in profiles): fail('PROFILE_NOT_FOUND',profile_id); return False
        active=profile_id; events.append({"op":"switch_profile","profile_id":profile_id}); return True

    def set_default_profile(profile_id):
        nonlocal default
        if not profile_id: fail('PROFILE_DEFAULT_INVALID','empty default'); return False
        if not any(p['profile_id']==profile_id for p in profiles): fail('PROFILE_DEFAULT_INVALID','not found'); return False
        default=profile_id; events.append({"op":"set_default_profile","profile_id":profile_id}); return True

    create_user('u1','TechGod')
    create_profile('p1','u1','Main')
    if mode=='fail':
        switch_profile('')
    else:
        switch_profile('p1')
        set_default_profile('p1')

    status='PASS' if len(failures)==0 else 'FAIL'
    audit={"timestamp_utc":now(),"status":status,"events":events,"failures":failures}
    smoke={
        "status":status,
        "active_profile":active,
        "default_profile":default,
        "users_count":len(users),
        "profiles_count":len(profiles),
        "profile_shell_policy_id": shell_cfg.get('policyId'),
        "workspace_surface": shell_cfg.get('workspaceSurface', {}),
        "save_policy": shell_cfg.get('savePolicy', {}),
        "profile_root_base": shell_cfg.get('profileRootBase'),
        "workspace_links": workspace_links,
        "profiles": profiles,
        "failures":failures,
        "audit_path":audit_path
    }
    try:
        write_json(audit_path,audit); write_json(smoke_path,smoke)
    except Exception as ex:
        fail('PROFILE_AUDIT_FAIL',str(ex))
        write_json(smoke_path,{"status":"FAIL","failures":failures})
        return CODES['PROFILE_AUDIT_FAIL']

    if failures:
        code=failures[0]['code']
        return CODES.get(code,1)
    return 0

if __name__=='__main__':
    raise SystemExit(main())

