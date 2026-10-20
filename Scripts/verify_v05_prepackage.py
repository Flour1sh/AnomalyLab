"""Current Editor preflight after a package-discovered fix; packaged full matrix remains required."""
import json,subprocess,sys,os
from datetime import datetime
from pathlib import Path
from checkpoint_v05 import ROOT,sha,write
def main():
    base=ROOT/'Saved/V05/T42';out=base/('Preflight_'+datetime.now().strftime('%Y%m%dT%H%M%S'));out.mkdir();module=sha(ROOT/'Binaries/Win64/UnrealEditor-AnomalyLab.dll');results=[]
    source={p.relative_to(ROOT).as_posix():sha(p) for folder in ('Source','Config','Content') for p in (ROOT/folder).rglob('*') if p.is_file()};write(out/'source_manifest.json',source)
    placement=json.loads((base/'latest_Placement.json').read_text(encoding='utf-8'));assert placement['status']=='PASS' and placement['module_sha256']==module and placement['trips']==20
    results.append(dict(name='Placement20',status='PASS',result=placement));env=os.environ.copy();env['PYTHONIOENCODING']='utf-8';env['PYTHONDONTWRITEBYTECODE']='1'
    jobs=[('Error',['run_v05.py','--task','T42','--mode','Error','--render']),('Loop',['run_v05.py','--task','T42','--mode','Loop','--render']),('Journey720',['run_v05.py','--task','T42','--mode','Journey','--render']),('Journey1080',['run_v05.py','--task','T42','--mode','Journey','--render','--width','1920','--height','1080']),('old_core_regions',['run_v05_baseline.py','--target','editor','--task','T42','--groups','core','regions'])]
    for name,args in jobs:
        command=[sys.executable,str(ROOT/'Scripts'/args[0])]+args[1:];log=out/(name+'.log');write(out/(name+'_command.json'),command);print('START '+name,flush=True)
        with log.open('wb') as f:code=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=900).returncode
        data=None
        for line in log.read_text(encoding='utf-8',errors='replace').splitlines():
            try:
                v=json.loads(line)
                if isinstance(v,dict) and v.get('status'):data=v
            except ValueError:pass
        good=code==0 and data and data['status']=='PASS';results.append(dict(name=name,status='PASS' if good else 'FAIL',result=data,log=str(log)));write(out/'report.json',dict(status='RUNNING' if good else 'FAIL',module_sha256=module,results=results));assert good,str(log)
    assert sha(ROOT/'Binaries/Win64/UnrealEditor-AnomalyLab.dll')==module
    assert all(sha(ROOT/p)==h for p,h in source.items())
    result=dict(status='PASS',module_sha256=module,source_manifest=str(out/'source_manifest.json'),results=results,human_samples=0);write(out/'report.json',result);write(base/'preflight_report.json',result);print(json.dumps(dict(status='PASS',report=str(out/'report.json'))),flush=True)
if __name__=='__main__':main()
