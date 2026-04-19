#!/usr/bin/env python3
import argparse, json, sys

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--report', required=True)
    args=ap.parse_args()
    with open(args.report,'r',encoding='utf-8-sig') as f:
        r=json.load(f)

    def chk(section):
        s=r.get(section)
        if s is None: return True, None
        failures=s.get('failures')
        if not isinstance(failures,list):
            return False, f'{section}.failures_not_list'
        status=str(s.get('status','UNKNOWN')).upper()
        if status=='PASS' and len(failures)!=0:
            return False, f'{section}.pass_nonempty_failures'
        if status=='FAIL':
            if len(failures)<1: return False, f'{section}.fail_empty_failures'
            if not all(isinstance(x,dict) and 'code' in x for x in failures):
                return False, f'{section}.failures_missing_code'
        return True, None

    for sec in ('users_profiles','services'):
        ok, err = chk(sec)
        if not ok:
            print(f'ASSERT_FAIL {err}')
            return 7
    print('ASSERT_PASS contract_report_shape')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
