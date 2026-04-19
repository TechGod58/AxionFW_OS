#!/usr/bin/env python3
import argparse, json, os
EXP={'fail':(61,'TASK_NOT_FOUND'),'kill_denied':(62,'TASK_KILL_DENIED'),'priority_invalid':(63,'TASK_PRIORITY_INVALID')}
ap=argparse.ArgumentParser(); ap.add_argument('--mode',required=True); ap.add_argument('--exit-code',type=int,required=True); ap.add_argument('--report',required=True); a=ap.parse_args()
if a.mode not in EXP: print('ASSERT_FAIL unknown_mode'); raise SystemExit(9)
eec,ecode=EXP[a.mode]
if a.exit_code!=eec: print(f'ASSERT_FAIL {a.mode}.exit expected={eec} got={a.exit_code}'); raise SystemExit(7)
if not os.path.exists(a.report): print('ASSERT_FAIL report_missing'); raise SystemExit(8)
r=json.load(open(a.report,'r',encoding='utf-8-sig'))
got=''
try: got=r['task_manager']['failures'][0]['code']
except Exception: pass
if got!=ecode: print(f'ASSERT_FAIL {a.mode}.code expected={ecode} got={got}'); raise SystemExit(7)
print(f'ASSERT_PASS {a.mode} exit={eec} code={ecode}')
