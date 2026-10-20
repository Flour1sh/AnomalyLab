"""Final packaged matrix. Every child keeps isolated evidence and save cleanup."""
import argparse,json,subprocess,sys,os,shutil,hashlib
from package_payload import is_runtime_file
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,required=True);a=p.parse_args();assert a.exe.is_file()
a.exe=a.exe.resolve()
out=ROOT/'Saved/V04/T32'/('Matrix_'+datetime.now().strftime('%Y%m%dT%H%M%S%f'));out.mkdir(parents=True)
EXE=['--exe',str(a.exe)];PY=sys.executable
baseline=str(ROOT/'Saved/V04/T26/Runs/20261012T094412728513_editor_logic_1280x720/report.json')
balance=str(ROOT/'Saved/V04/T31/Runs/20261012T094855549302_editor/report.json')
jobs=[]
for width,height in [(1280,720),(1920,1080)]:
    dims=['--width',str(width),'--height',str(height)]
    jobs += [(f'menu_{height}',[PY,'Scripts/run_t19_menu.py']+dims+EXE),
             (f'core_{height}',[PY,'Scripts/run_v03.py','--from-menu','--render','--mute']+dims+EXE),
             (f'observer_{height}',[PY,'Scripts/run_t30.py','--render']+dims+EXE),
             (f'regions_{height}',[PY,'Scripts/run_t26.py','--render','--compare',baseline]+dims+EXE)]
jobs += [('resources',[PY,'Scripts/run_v04.py','--stage','T27']+EXE),
         ('equipment_720',[PY,'Scripts/run_v04.py','--stage','T28','--render']+EXE),
         ('equipment_1080',[PY,'Scripts/run_v04.py','--stage','T28','--render','--width','1920','--height','1080']+EXE),
         ('save_suite',[PY,'Scripts/run_t29.py']+EXE),
         ('balance',[PY,'Scripts/run_t31.py','--compare',balance]+EXE),
         ('cold_boot',[PY,'Scripts/cold_boot_v04.py']+EXE)]
for suite in ['stats','decision','flow']:jobs.append(('legacy_'+suite,[PY,'Scripts/run_t18.py','packaged',suite,'--map','/Game/Prototype/Maps/L_LegacyPrototype']+EXE))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
package=a.exe.parent
def payload():return {p.relative_to(package).as_posix():sha(p) for p in package.rglob('*') if p.is_file() and not is_runtime_file(p.relative_to(package))}
before=payload()
env=os.environ.copy();env['PYTHONIOENCODING']='utf-8'
def run(job):
    name,cmd=job;target=out/name;target.mkdir();(target/'command.json').write_text(json.dumps(cmd,ensure_ascii=False,indent=2),encoding='utf-8')
    with (target/'runner.log').open('wb') as f:proc=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    data=None
    for line in (target/'runner.log').read_text(encoding='utf-8',errors='replace').splitlines():
        try:
            obj=json.loads(line)
            if isinstance(obj,dict) and obj.get('status'):data=obj
        except ValueError:pass
    if name=='save_suite' and proc.returncode==0:data=json.loads((ROOT/'Saved/V04/T29/latest_save_suite.json').read_text(encoding='utf-8'))
    if name.startswith('legacy_') and data and proc.returncode==0:
        for key in ['report','log']:
            source=Path(data[key]);dest=target/source.name;shutil.copy2(source,dest);data[key]=str(dest)
    result=dict(name=name,status='PASS' if proc.returncode==0 and data and data['status']=='PASS' else 'FAIL',exit_code=proc.returncode,result=data,evidence=str(target))
    (target/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');return result
results=[]
print('Matrix evidence: '+str(out),flush=True)
with ThreadPoolExecutor(max_workers=3) as pool:
    for future in as_completed([pool.submit(run,j) for j in jobs]):
        result=future.result();results.append(result);print(json.dumps(dict(name=result['name'],status=result['status']),ensure_ascii=True),flush=True)
after=payload()
stable=before==after
report=dict(status='PASS' if stable and all(r['status']=='PASS' for r in results) else 'FAIL',exe=str(a.exe),results=results,package_unchanged=stable,package_sha256=before,human_samples=0)
(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if report['status']=='PASS':(ROOT/'Saved/V04/T32/latest_matrix.json').write_text(json.dumps(dict(status='PASS',directory=str(out),report=str(out/'report.json')),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(status=report['status'],directory=str(out)),ensure_ascii=True));assert report['status']=='PASS',str(out)
