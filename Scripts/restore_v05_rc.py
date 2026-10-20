"""Copy complete source and package into NEW directories, SHA readback then actual boot."""
import json,shutil,subprocess,sys,os
from datetime import datetime
from pathlib import Path
from checkpoint_v05 import ROOT,files,sha,write
from package_payload import is_runtime_file
def main():
    base=ROOT/'Saved/V05/T42';pkg=json.loads((base/'package_report.json').read_text(encoding='utf-8'));matrix=json.loads((base/'latest_matrix.json').read_text(encoding='utf-8'));assert pkg['status']==matrix['status']=='PASS'
    out=base/('Restore_'+datetime.now().strftime('%Y%m%dT%H%M%S'));out.mkdir(exist_ok=False);records=[]
    def copy(src,rel):
        dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);h=sha(src);shutil.copy2(src,dest);assert sha(dest)==h and sha(src)==h
        records.append(dict(path=rel.as_posix(),bytes=src.stat().st_size,sha256=h))
    for src in files(ROOT):copy(src,Path('Project')/src.relative_to(ROOT))
    original=Path(pkg['exe']).parent
    for src in original.rglob('*'):
        if src.is_file() and not is_runtime_file(src.relative_to(original)):copy(src,Path('Windows')/src.relative_to(original))
    expected=json.loads(Path(pkg['payload_manifest']).read_text(encoding='utf-8'))['files']
    assert {r['path'].removeprefix('Windows/'):r['sha256'] for r in records if r['path'].startswith('Windows/')}=={r['path']:r['sha256'] for r in expected}
    write(out/'copy_manifest.json',dict(files=records));assert all(sha(out/r['path'])==r['sha256'] for r in records)
    results=[];env=os.environ.copy();env['PYTHONIOENCODING']='utf-8';env['PYTHONDONTWRITEBYTECODE']='1'
    for name,script,args in [('source_hub',out/'Project/Scripts/run_t34.py',['--mode','Hub','--task','T42']),('package_journey',ROOT/'Scripts/run_v05.py',['--task','T42','--mode','Journey','--render','--exe',str(out/'Windows/AnomalyLab.exe')]),('package_direct',ROOT/'Scripts/run_v05.py',['--task','T42','--mode','Direct','--exe',str(out/'Windows/AnomalyLab.exe')])]:
        command=[sys.executable,str(script)]+args;log=out/(name+'.log');write(out/(name+'_command.json'),command);print('START '+name,flush=True)
        with log.open('wb') as f:code=subprocess.run(command,cwd=script.parents[1],env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=500).returncode
        data=None
        for line in log.read_text(encoding='utf-8',errors='replace').splitlines():
            try:
                v=json.loads(line)
                if isinstance(v,dict) and v.get('status'):data=v
            except ValueError:pass
        good=code==0 and data and data['status']=='PASS';results.append(dict(name=name,status='PASS' if good else 'FAIL',result=data,log=str(log)))
        write(out/'report.json',dict(status='RUNNING' if good else 'FAIL',results=results));assert good,str(log)
    assert all(sha(out/r['path'])==r['sha256'] for r in records),'Restored payload drift'
    result=dict(status='PASS',directory=str(out),files=len(records),project_files=sum(r['path'].startswith('Project/') for r in records),package_files=len(expected),results=results,scope='Complete source+package SHA in new directories; restored source Editor Hub and packaged Journey/direct-route boot. Source recompilation requires a new build context, not executed here.')
    write(out/'report.json',result);write(base/'restore_report.json',result);print(json.dumps(dict(status='PASS',report=str(out/'report.json'),directory=str(out))),flush=True)
if __name__=='__main__':main()
