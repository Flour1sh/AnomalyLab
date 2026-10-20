"""Save boundaries and two separate OS processes proving purchase -> cold restart recovery."""
import argparse,json,subprocess,sys
from pathlib import Path
from datetime import datetime
from test_save_slots import new_slot,cleanup_slot
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path);a=p.parse_args()
out=ROOT/'Saved/V04/T29'/('Suite_'+datetime.now().strftime('%Y%m%dT%H%M%S%f'));out.mkdir(parents=True)
slots={group:new_slot('Cold29_'+group) for group in ['purchase','quit','migrate','future']}; results=[]
cases=[('boundaries',None,False),('write','purchase',True),('read','purchase',False),('quit_write','quit',True),('quit_read','quit',False),
       ('migrate_write','migrate',True),('migrate_read','migrate',False),('future_write','future',True),('future_read','future',False),('extract_fail',None,False)]
try:
    for case,group,keep in cases:
        cmd=[sys.executable,str(ROOT/'Scripts/run_v04.py'),'--stage','T29','--save-case',case]
        if group:cmd += ['--slot',slots[group]]
        if keep:cmd += ['--keep-slot']
        if a.exe:cmd += ['--exe',str(a.exe)]
        proc=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        (out/(case+'.log')).write_bytes(proc.stdout);assert proc.returncode==0,case
        data=json.loads((ROOT/'Saved/V04/T29/latest_native.json').read_text(encoding='utf-8'))
        results.append(dict(case=case,**data));print(json.dumps(results[-1],ensure_ascii=True),flush=True)
finally:
    removed=[path for slot in slots.values() for path in cleanup_slot(slot,exe=a.exe)]
report=dict(status='PASS',processes=len(results),results=results,final_cleanup=removed,human_samples=0)
(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Saved/V04/T29/latest_save_suite.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
