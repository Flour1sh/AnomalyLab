"""Sequential reuse of unchanged v0.4 assertions against isolated v0.5 workspace."""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--target',choices=['package','editor'],required=True)
    p.add_argument('--task',default='T33',choices=['T33','T34','T35','T36','T37','T38','T39','T40','T41','T42'])
    p.add_argument('--exe',type=Path)
    p.add_argument('--groups',nargs='+',default=['resources','equipment','save','regions','observer','balance','core','menu','legacy_stats','legacy_decision','legacy_flow'])
    a=p.parse_args()
    out=ROOT/'Saved/V05'/a.task/('Regression_'+a.target+'_'+datetime.now().strftime('%Y%m%dT%H%M%S'))
    out.mkdir(parents=True,exist_ok=False)
    exe=(a.exe or ROOT/'Saved/V05/T33/BaselinePackage/Windows/AnomalyLab.exe').resolve()
    if a.target=='package': assert exe.is_file() and exe.is_relative_to(ROOT) and exe.name=='AnomalyLab.exe',str(exe)
    extra=['--exe',str(exe)] if a.target=='package' else []
    render=['--render','--width','1280','--height','720']
    scripts={
      'resources':['run_v04.py','--stage','T27'],
      'equipment':['run_v04.py','--stage','T28']+render,
      'save':['run_t29.py'],
      'regions':['run_t26.py','--compare',str(ROOT.parent/'我的项目3/Saved/V04/T26/Runs/20261012T094412728513_editor_logic_1280x720/report.json')],
      'observer':['run_t30.py']+render,
      'balance':['run_t31.py','--compare',str(ROOT.parent/'我的项目3/Saved/V04/T31/Runs/20261012T094855549302_editor/report.json')],
      'core':['run_v03.py','--from-menu','--mute']+render,
      'menu':['run_t19_menu.py','--width','1280','--height','720'],
    }
    if a.task!='T33':
        scripts['core']+=['--legacy-menu-route']
        scripts['menu']+=['--legacy-menu-route']
    for suite in ['stats','decision','flow']:
        scripts['legacy_'+suite]=['run_t18.py','packaged' if a.target=='package' else 'editor',suite,'--map','/Game/Prototype/Maps/L_LegacyPrototype']
    results=[]; env=os.environ.copy(); env['PYTHONIOENCODING']='utf-8'; env['PYTHONDONTWRITEBYTECODE']='1'
    for group in a.groups:
        args=scripts[group]; command=[sys.executable,str(ROOT/'Scripts'/args[0])]+args[1:]+extra
        folder=out/group; folder.mkdir(); (folder/'command.json').write_text(json.dumps(command,ensure_ascii=False,indent=2),encoding='utf-8')
        print('START '+a.target+' '+group,flush=True)
        with (folder/'runner.log').open('wb') as stream:
            proc=subprocess.Popen(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            try: code=proc.wait(timeout=660)
            except subprocess.TimeoutExpired:
                # Each existing child has its own shorter UE timeout and cleanup.
                proc.kill(); proc.wait(); code=-1
        data=None
        for line in (folder/'runner.log').read_text(encoding='utf-8',errors='replace').splitlines():
            try:
                obj=json.loads(line)
                if isinstance(obj,dict) and obj.get('status'): data=obj
            except ValueError: pass
        if group=='save' and code==0:
            data=json.loads((ROOT/'Saved/V04/T29/latest_save_suite.json').read_text(encoding='utf-8'))
        good=code==0 and data is not None and data.get('status')=='PASS'
        results.append(dict(group=group,status='PASS' if good else 'FAIL',exit_code=code,result=data,runner_log=str(folder/'runner.log')))
        report=dict(status='PASS' if good and len(results)==len(a.groups) else 'RUNNING' if good else 'FAIL',target=a.target,exe=str(exe) if a.target=='package' else None,results=results,human_samples=0)
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(dict(group=group,status=results[-1]['status'],checks=data.get('checks') if data else None),ensure_ascii=True),flush=True)
        if not good: raise RuntimeError(str(folder/'runner.log'))
    (ROOT/'Saved/V05'/a.task/('latest_regression_'+a.target+'.json')).write_text(json.dumps(dict(status='PASS',report=str(out/'report.json')),indent=2),encoding='utf-8')
    print(json.dumps(dict(status='PASS',groups=len(results),report=str(out/'report.json')),ensure_ascii=True),flush=True)

if __name__=='__main__': main()
