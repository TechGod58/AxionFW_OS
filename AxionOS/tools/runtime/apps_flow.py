from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone

CODES={
  "APP_NOT_FOUND":91,
  "APP_LAUNCH_DENIED":92,
  "APP_INSTALL_INVALID":93,
  "APP_AUDIT_FAIL":94,
}

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def write(path,obj):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    with open(path,'w',encoding='utf-8') as f: json.dump(obj,f,indent=2)

def main():
    base=axion_path_str('out', 'runtime')
    audit=os.path.join(base,'apps_audit.json')
    smoke=os.path.join(base,'apps_smoke.json')
    mode='pass'
    if len(sys.argv)>1: mode=sys.argv[1]

    apps=[{'app_id':'app.notes','name':'Notes','installed':True,'enabled':True},{'app_id':'app.calc','name':'Calculator','installed':True,'enabled':True}]
    failures=[]; events=[]; active=None
    def fail(code,detail): failures.append({'code':code,'detail':detail})

    def list_apps(): events.append({'op':'list_apps','count':len(apps)}); return apps
    def launch(app_id):
        nonlocal active
        a=next((x for x in apps if x['app_id']==app_id),None)
        if not a: fail('APP_NOT_FOUND',app_id); return False
        if not a.get('enabled',True): fail('APP_LAUNCH_DENIED',app_id); return False
        active=app_id; events.append({'op':'launch','app_id':app_id}); return True

    list_apps()
    if mode=='fail':
        launch('app.missing')
    else:
        launch('app.notes')

    st='FAIL' if failures else 'PASS'
    smoke_obj={'timestamp_utc':now(),'status':st,'apps':apps,'active_app_id':active,'failures':failures,'audit_path':audit}
    audit_obj={'timestamp_utc':now(),'status':st,'events':events,'failures':failures}
    try:
        write(smoke,smoke_obj); write(audit,audit_obj)
    except Exception as ex:
        fail('APP_AUDIT_FAIL',str(ex)); write(smoke,{'timestamp_utc':now(),'status':'FAIL','failures':failures}); return CODES['APP_AUDIT_FAIL']

    if failures: return CODES.get(failures[0]['code'],1)
    return 0

if __name__=='__main__':
    raise SystemExit(main())

