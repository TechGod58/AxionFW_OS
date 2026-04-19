from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone

CODES = {
"SERVICE_NOT_FOUND": 41,
"SERVICE_STATE_INVALID": 42,
"SERVICE_START_DENIED": 43,
"SERVICE_STOP_DENIED": 44,
"SERVICE_RESTART_INVALID": 45,
"SERVICE_STARTUP_INVALID": 46,
"SERVICE_AUDIT_FAIL": 47,
}

STATES = {"running","stopped","failed","disabled"}
STARTUP = {"auto","manual","disabled"}

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

def write_json(path,obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,'w',encoding='utf-8') as f: json.dump(obj,f,indent=2)


def main():
    base=axion_path_str('out', 'runtime')
    audit_path=os.path.join(base,'services_audit.json')
    smoke_path=os.path.join(base,'services_smoke.json')
    mode='pass'
    if len(sys.argv)>1: mode=sys.argv[1]

    services={
      "svc.shell": {"display_name":"Shell Host","state":"running","startup_type":"auto","health":"ok","last_error":None},
      "svc.eventbus": {"display_name":"Event Bus","state":"running","startup_type":"auto","health":"ok","last_error":None},
      "svc.updates": {"display_name":"Updates Host","state":"stopped","startup_type":"manual","health":"ok","last_error":None},
    }
    failures=[]; events=[]
    def fail(code,detail): failures.append({"code":code,"detail":detail})

    def get_service(sid):
        s=services.get(sid)
        if not s: fail("SERVICE_NOT_FOUND",sid)
        return s

    def set_startup_type(sid, st):
        s=get_service(sid)
        if not s: return False
        if st not in STARTUP: fail("SERVICE_STARTUP_INVALID",st); return False
        s["startup_type"]=st; events.append({"op":"set_startup_type","service_id":sid,"startup_type":st}); return True

    def start_service(sid):
        s=get_service(sid)
        if not s: return False
        if s["state"]=="disabled": fail("SERVICE_START_DENIED",sid); return False
        s["state"]="running"; events.append({"op":"start_service","service_id":sid}); return True

    def stop_service(sid):
        s=get_service(sid)
        if not s: return False
        if sid=="svc.shell": fail("SERVICE_STOP_DENIED",sid); return False
        s["state"]="stopped"; events.append({"op":"stop_service","service_id":sid}); return True

    def restart_service(sid):
        s=get_service(sid)
        if not s: return False
        if s["state"] not in STATES: fail("SERVICE_STATE_INVALID",sid); return False
        if not stop_service(sid): fail("SERVICE_RESTART_INVALID",sid); return False
        if not start_service(sid): fail("SERVICE_RESTART_INVALID",sid); return False
        events.append({"op":"restart_service","service_id":sid}); return True

    # flow
    set_startup_type('svc.updates','auto')
    restart_service('svc.updates')
    if mode=='fail':
        # deterministic negative control
        get_service('svc.missing')
    elif mode=='start_denied':
        services['svc.updates']['state'] = 'disabled'
        start_service('svc.updates')
    elif mode=='stop_denied':
        stop_service('svc.shell')
    elif mode=='startup_invalid':
        set_startup_type('svc.updates','invalid_type')
    else:
        start_service('svc.eventbus')

    status='PASS' if not failures else 'FAIL'
    audit={"timestamp_utc":now(),"status":status,"events":events,"failures":failures}
    smoke={"status":status,"services":services,"failures":failures,"audit_path":audit_path}
    try:
        write_json(audit_path,audit)
        write_json(smoke_path,smoke)
    except Exception as ex:
        fail("SERVICE_AUDIT_FAIL",str(ex))
        write_json(smoke_path,{"status":"FAIL","failures":failures})
        return CODES["SERVICE_AUDIT_FAIL"]

    if failures:
        return CODES.get(failures[0]['code'],1)
    return 0

if __name__=='__main__':
    raise SystemExit(main())


