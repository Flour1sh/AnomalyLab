"""Copy candidate into NEW directories, verify every copy, and boot relocated package."""
import argparse,json,shutil,subprocess,sys,os
from pathlib import Path
from datetime import datetime
from archive_v04_rc import ROOT,OUT,sha,write,project_files
from package_payload import is_runtime_file
p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);a=p.parse_args()
target=OUT/('RestoreValidation_'+datetime.now().strftime('%Y%m%dT%H%M%S'));target.mkdir(parents=True,exist_ok=False)
records=[]
for src in project_files():
    rel=Path('Project')/src.relative_to(ROOT);dst=target/rel;dst.parent.mkdir(parents=True,exist_ok=True);digest=sha(src);shutil.copy2(src,dst);assert sha(dst)==digest
    records.append(dict(path=rel.as_posix(),sha256=digest))
for src in (a.package/'Windows').rglob('*'):
    if src.is_file() and not is_runtime_file(src.relative_to(a.package/'Windows')):
        rel=Path('Windows')/src.relative_to(a.package/'Windows');dst=target/rel;dst.parent.mkdir(parents=True,exist_ok=True);digest=sha(src);shutil.copy2(src,dst);assert sha(dst)==digest
        records.append(dict(path=rel.as_posix(),sha256=digest))
write(target/'copy_manifest.json',records)
exe=target/'Windows/AnomalyLab.exe';results=[];env=os.environ.copy();env['PYTHONIOENCODING']='utf-8'
for name,script,args in [('cold_boot','cold_boot_v04.py',[]),('resources','run_v04.py',['--stage','Restore_T27'])]:
    with (target/(name+'.log')).open('wb') as f:code=subprocess.run([sys.executable,str(ROOT/'Scripts'/script),'--exe',str(exe)]+args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,env=env,creationflags=subprocess.CREATE_NO_WINDOW).returncode
    assert code==0,name
    data=None
    for line in (target/(name+'.log')).read_text(encoding='utf-8',errors='replace').splitlines():
        try:
            obj=json.loads(line)
            if isinstance(obj,dict) and obj.get('status'):data=obj
        except ValueError:pass
    assert data and data['status']=='PASS',name
    results.append(dict(name=name,status='PASS',log=str(target/(name+'.log')),result=data))
assert all(sha(target/r['path'])==r['sha256'] for r in records),'Restored payload mutated'
report=dict(status='PASS',directory=str(target),files=len(records),results=results,scope='Source/assets/scripts/docs/binaries/model/audio and complete package copied to NEW directories with SHA verification; relocated package default boot and resource/equipment integration passed. Restored source not separately recompiled; final archive documents may be updated after this copy.')
write(OUT/'restore_report.json',report);print(json.dumps(report,ensure_ascii=True))
