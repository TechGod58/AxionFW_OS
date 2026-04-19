#!/usr/bin/env python3
import argparse, json, os, sys
EXPECTED={
  "start_denied": (43,"SERVICE_START_DENIED"),
  "stop_denied": (44,"SERVICE_STOP_DENIED"),
  "startup_invalid": (46,"SERVICE_STARTUP_INVALID"),
}

def main():
  ap=argparse.ArgumentParser(); ap.add_argument('--mode',required=True); ap.add_argument('--exit-code',type=int,required=True); ap.add_argument('--report',required=True); a=ap.parse_args()
  if a.mode not in EXPECTED:
    print('ASSERT_FAIL unknown_mode'); return 9
  exp_ec, exp_code = EXPECTED[a.mode]
  if a.exit_code != exp_ec:
    print(f'ASSERT_FAIL {a.mode}.exit expected={exp_ec} got={a.exit_code}'); return 7
  if not os.path.exists(a.report):
    print('ASSERT_FAIL report_missing'); return 8
  r=json.load(open(a.report,'r',encoding='utf-8-sig'))
  got=''
  try: got=r['services']['failures'][0]['code']
  except Exception: pass
  if got != exp_code:
    print(f'ASSERT_FAIL {a.mode}.code expected={exp_code} got={got}'); return 7
  print(f'ASSERT_PASS {a.mode} exit={exp_ec} code={exp_code}')
  return 0
if __name__=='__main__': raise SystemExit(main())
