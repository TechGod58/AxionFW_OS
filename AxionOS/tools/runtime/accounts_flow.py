from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone

CODES={
  "ACCOUNT_CREATE_INVALID":71,
  "ACCOUNT_ALREADY_EXISTS":72,
  "ACCOUNT_NOT_FOUND":73,
  "ACCOUNT_DEFAULT_INVALID":74,
  "ACCOUNT_DISABLE_INVALID":75,
  "ACCOUNT_AUDIT_FAIL":76,
}

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

def write(path,obj):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    with open(path,'w',encoding='utf-8') as f: json.dump(obj,f,indent=2)

def main():
    base=axion_path_str('out', 'runtime')
    audit=os.path.join(base,'accounts_audit.json')
    smoke=os.path.join(base,'accounts_smoke.json')
    mode='pass'
    if len(sys.argv)>1: mode=sys.argv[1]

    accounts=[]; failures=[]; events=[]; active=None; default=None
    def fail(code,detail): failures.append({"code":code,"detail":detail})

    def create(acc_id,name):
        if not acc_id or not name: fail('ACCOUNT_CREATE_INVALID','empty fields'); return False
        if any(a['account_id']==acc_id for a in accounts): fail('ACCOUNT_ALREADY_EXISTS',acc_id); return False
        accounts.append({'account_id':acc_id,'name':name,'enabled':True,'created_utc':now()}); events.append({'op':'create','account_id':acc_id}); return True

    def switch(acc_id):
        nonlocal active
        a=next((x for x in accounts if x['account_id']==acc_id),None)
        if not a: fail('ACCOUNT_NOT_FOUND',acc_id); return False
        if not a.get('enabled',True): fail('ACCOUNT_DISABLE_INVALID',acc_id); return False
        active=acc_id; events.append({'op':'switch','account_id':acc_id}); return True

    def set_default(acc_id):
        nonlocal default
        if not any(a['account_id']==acc_id for a in accounts): fail('ACCOUNT_DEFAULT_INVALID',acc_id); return False
        default=acc_id; events.append({'op':'set_default','account_id':acc_id}); return True

    def disable(acc_id):
        a=next((x for x in accounts if x['account_id']==acc_id),None)
        if not a: fail('ACCOUNT_NOT_FOUND',acc_id); return False
        a['enabled']=False; events.append({'op':'disable','account_id':acc_id}); return True

    # baseline flow
    create('acc_main','Main Account')
    create('acc_alt','Alt Account')

    if mode=='fail':
        switch('acc_missing')  # deterministic negative
    else:
        switch('acc_main')
        set_default('acc_main')
        disable('acc_alt')

    status='FAIL' if failures else 'PASS'
    smoke_obj={'timestamp_utc':now(),'status':status,'accounts':accounts,'active_account_id':active,'default_account_id':default,'failures':failures,'audit_path':audit}
    audit_obj={'timestamp_utc':now(),'status':status,'events':events,'failures':failures}
    try:
        write(smoke,smoke_obj); write(audit,audit_obj)
    except Exception as ex:
        fail('ACCOUNT_AUDIT_FAIL',str(ex))
        write(smoke,{'timestamp_utc':now(),'status':'FAIL','failures':failures})
        return CODES['ACCOUNT_AUDIT_FAIL']

    if failures: return CODES.get(failures[0]['code'],1)
    return 0

if __name__=='__main__':
    raise SystemExit(main())

