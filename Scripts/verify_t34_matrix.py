"""Sequential new-map gate. Stops on any failure; retains all child logs."""
import argparse,json,os,subprocess,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--skip-assets',action='store_true');p.add_argument('--regression',action='store_true');a=p.parse_args()
out=ROOT/'Saved/V05/T34'/('Matrix_'+datetime.now().strftime('%Y%m%dT%H%M%S'));out.mkdir(parents=True,exist_ok=False)
jobs=[]
if not a.skip_assets:
    jobs+=[('build',['cpp_migration.py','editor','--script','build_v05_levels.py','--phase','t34_final_build']),('reload',['cpp_migration.py','editor','--script','verify_t34_assets.py','--phase','t34_final_reload'])]
for width,height in [(1280,720),(1920,1080)]:
    for mode in ['Hub','Lab','Menu']:jobs.append((f'{mode}_{height}',['run_t34.py','--mode',mode,'--width',str(width),'--height',str(height)]))
if a.regression:jobs.append(('legacy_regression',['run_v05_baseline.py','--target','editor','--task','T34']))
results=[];env=os.environ.copy();env['PYTHONIOENCODING']='utf-8';env['PYTHONDONTWRITEBYTECODE']='1'
for name,args in jobs:
    cmd=[sys.executable,str(ROOT/'Scripts'/args[0])]+args[1:];log=out/(name+'.log')
    (out/(name+'_command.json')).write_text(json.dumps(cmd,ensure_ascii=False,indent=2),encoding='utf-8');print('START '+name,flush=True)
    with log.open('wb') as f:
        proc=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,env=env,creationflags=subprocess.CREATE_NO_WINDOW,timeout=1200 if name=='legacy_regression' else 300)
    data=None
    if name not in ['build','reload']:
        for line in log.read_text(encoding='utf-8',errors='replace').splitlines():
            try:
                obj=json.loads(line)
                if isinstance(obj,dict) and obj.get('status'):data=obj
            except ValueError:pass
    elif name=='reload':data=json.loads((ROOT/'Saved/V05/T34/asset_reload.json').read_text(encoding='utf-8')) if proc.returncode==0 else None
    else:data=json.loads((ROOT/'Saved/V05/T34/latest_build.json').read_text(encoding='utf-8')) if proc.returncode==0 else None
    good=proc.returncode==0 and data is not None and data.get('status')=='PASS'
    results.append(dict(name=name,status='PASS' if good else 'FAIL',exit_code=proc.returncode,result=data,log=str(log)))
    report=dict(status='PASS' if good and len(results)==len(jobs) else 'RUNNING' if good else 'FAIL',results=results,human_samples=0)
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(dict(name=name,status=results[-1]['status']),ensure_ascii=True),flush=True)
    assert good,str(log)
(ROOT/'Saved/V05/T34/latest_matrix.json').write_text(json.dumps(dict(status='PASS',report=str(out/'report.json')),indent=2),encoding='utf-8')
print(json.dumps(dict(status='PASS',groups=len(results),report=str(out/'report.json')),ensure_ascii=True),flush=True)
