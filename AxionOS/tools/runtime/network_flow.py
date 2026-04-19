from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

CODES={
  "NETWORK_ADAPTER_NOT_FOUND":81,
  "NETWORK_DNS_INVALID":82,
  "NETWORK_PERMISSION_DENIED":83,
  "NETWORK_AUDIT_FAIL":84,
}
IDENTITY_PATH = Path(axion_path_str('config', 'INSTALL_IDENTITY_V1.json'))
REMOTE_PATH = Path(axion_path_str('config', 'REMOTE_DESKTOP_STATE_V1.json'))

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

def write(path,obj):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    with open(path,'w',encoding='utf-8') as f: json.dump(obj,f,indent=2)

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def main():
    base=axion_path_str('out', 'runtime')
    audit=os.path.join(base,'network_audit.json')
    smoke=os.path.join(base,'network_smoke.json')
    mode='pass'
    if len(sys.argv)>1: mode=sys.argv[1]

    adapters=[
      {"adapter_id":"eth0","name":"Ethernet 0","enabled":True,"up":True},
      {"adapter_id":"wifi0","name":"Wi-Fi 0","enabled":True,"up":False}
    ]
    dns=["1.1.1.1","8.8.8.8"]
    identity = load(IDENTITY_PATH).get('install', {})
    remote = load(REMOTE_PATH).get('remote_desktop', {})
    failures=[]; events=[]
    def fail(code,detail): failures.append({"code":code,"detail":detail})

    def status():
      return {"up":sum(1 for a in adapters if a['up']),"total":len(adapters)}

    def list_adapters():
      events.append({"op":"list_adapters","count":len(adapters)}); return adapters

    def set_dns(values):
      if not isinstance(values,list) or len(values)==0: fail('NETWORK_DNS_INVALID','empty dns list'); return False
      for v in values:
        if not isinstance(v,str) or len(v.split('.'))!=4: fail('NETWORK_DNS_INVALID',f'bad dns {v}'); return False
      nonlocal_dns.clear(); nonlocal_dns.extend(values)
      events.append({"op":"set_dns","values":values}); return True

    def toggle_adapter(adapter_id,enabled):
      a=next((x for x in adapters if x['adapter_id']==adapter_id),None)
      if not a: fail('NETWORK_ADAPTER_NOT_FOUND',adapter_id); return False
      a['enabled']=bool(enabled)
      a['up']=a['up'] if a['enabled'] else False
      events.append({"op":"toggle_adapter","adapter_id":adapter_id,"enabled":a['enabled']}); return True

    nonlocal_dns=dns
    list_adapters()
    if mode=='fail':
      toggle_adapter('missing0',False)
    elif mode=='dns_invalid':
      set_dns(['not_an_ip'])
    elif mode=='permission_denied':
      fail('NETWORK_PERMISSION_DENIED','operation denied by policy')
    else:
      toggle_adapter('wifi0',True)
      set_dns(['9.9.9.9','1.1.1.1'])

    st='FAIL' if failures else 'PASS'
    smoke_obj={'timestamp_utc':now(),'status':st,'network_status':status(),'adapters':adapters,'dns':nonlocal_dns,'computer_name':identity.get('computer_name'),'workgroup':identity.get('workgroup'),'remote_desktop':remote,'failures':failures,'audit_path':audit}
    audit_obj={'timestamp_utc':now(),'status':st,'events':events + [{'op': 'identity_loaded', 'computer_name': identity.get('computer_name')}, {'op': 'remote_desktop_state', 'enabled': remote.get('enabled')}],'failures':failures}
    try:
      write(smoke,smoke_obj); write(audit,audit_obj)
    except Exception as ex:
      fail('NETWORK_AUDIT_FAIL',str(ex)); write(smoke,{'timestamp_utc':now(),'status':'FAIL','failures':failures}); return CODES['NETWORK_AUDIT_FAIL']
    if failures: return CODES.get(failures[0]['code'],1)
    return 0

if __name__=='__main__':
    raise SystemExit(main())

