"""Sequential tests against one exact full Windows candidate; keeps every failed run."""
import argparse,json,subprocess,sys,os
from datetime import datetime
from pathlib import Path
from checkpoint_v05 import ROOT,sha,write,protected
from test_save_slots import new_slot,cleanup_slot
def main():
    p=argparse.ArgumentParser();p.add_argument('--exe',type=Path);p.add_argument('--reuse',type=Path);a=p.parse_args()
    base=ROOT/'Saved/V05/T42';pkg=json.loads((base/'package_report.json').read_text(encoding='utf-8'));assert pkg['status']=='PASS'
    exe=(a.exe or Path(pkg['exe'])).resolve();assert exe==Path(pkg['exe']).resolve() and exe.is_file()
    out=base/('Matrix_'+datetime.now().strftime('%Y%m%dT%H%M%S'));out.mkdir();results=[];prior={}
    payload=json.loads(Path(pkg['payload_manifest']).read_text(encoding='utf-8'))['files']
    assert all(sha(exe.parent/r['path'])==r['sha256'] for r in payload)
    if a.reuse:
        old=json.loads(a.reuse.read_text(encoding='utf-8'));assert Path(old['exe']).resolve()==exe and old['payload_manifest']==pkg['payload_manifest']
        prior={r['name']:r for r in old['results'] if r['status']=='PASS'}
    env=os.environ.copy();env['PYTHONIOENCODING']='utf-8';env['PYTHONDONTWRITEBYTECODE']='1'
    def job(name,args,reuse=True):
        if reuse and name in prior:
            r=prior[name];assert all(Path(r['result'][key]).exists() for key in ['report'] if key in r['result']);results.append(r);print('REUSE '+name,flush=True);return r['result']
        cmd=[sys.executable,str(ROOT/'Scripts'/args[0])]+args[1:]+['--exe',str(exe)];write(out/(name+'_command.json'),cmd);log=out/(name+'.log');print('START '+name,flush=True)
        with log.open('wb') as stream:code=subprocess.run(cmd,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=2400).returncode
        data=None
        for line in log.read_text(encoding='utf-8',errors='replace').splitlines():
            try:
                obj=json.loads(line)
                if isinstance(obj,dict) and obj.get('status'):data=obj
            except ValueError:pass
        good=code==0 and data is not None and data['status']=='PASS';results.append(dict(name=name,status='PASS' if good else 'FAIL',exit_code=code,result=data,log=str(log)))
        write(out/'report.json',dict(status='RUNNING' if good else 'FAIL',exe=str(exe),payload_manifest=pkg['payload_manifest'],results=results,human_samples=0))
        print(json.dumps(dict(name=name,status=results[-1]['status'])),flush=True);assert good,str(log);return data
    for mode in ['Loop','Error','Import']:
        args=['run_v05.py','--task','T42','--mode',mode]
        if mode in ['Loop','Error']:args+=['--render']
        job(mode,args)
    job('ProductionImportCLI',['verify_v05_import_cli.py'])
    job('AbruptCrash',['verify_v05_crash.py'])
    for mode in ['Shop','Placement','Power','Chamber','Events','Quiet','Journey','Direct','Corrupt']:
        args=['run_v05.py','--task','T42','--mode',mode]
        if mode not in ['Direct','Import','Corrupt']:args+=['--render']
        job(mode,args)
    job('Journey1080',['run_v05.py','--task','T42','--mode','Journey','--render','--width','1920','--height','1080'])
    for mode in ['Loop','Shop','Events']:
        job(mode+'1080',['run_v05.py','--task','T42','--mode',mode,'--render','--width','1920','--height','1080'])
    slot=new_slot('T42Restart')
    try:
        job('RestartWrite',['run_v05.py','--task','T42','--mode','RestartWrite','--slot',slot,'--keep-slot'],False)
        job('RestartRead',['run_v05.py','--task','T42','--mode','RestartRead','--slot',slot],False)
    finally:cleanup_slot(slot,exe=exe)
    job('TelemetryDisabled',['run_v05.py','--task','T42','--mode','Loop','--no-telemetry'])
    job('TelemetryAudit',['verify_v05_telemetry.py','--task','T42'])
    for width,height in [(1280,720),(1920,1080)]:
        for mode in ['Menu','Hub','Lab']:job(mode+str(height),['run_t34.py','--task','T42','--mode',mode,'--width',str(width),'--height',str(height)])
    job('old_regression11',['run_v05_baseline.py','--target','package','--task','T42'])
    job('RuntimeSignals',['audit_v05_runtime.py','--task','T42'])
    assert all(sha(ROOT/name)==digest for name,digest in json.loads(Path(pkg['source_manifest']).read_text(encoding='utf-8')).items())
    assert all(sha(exe.parent/r['path'])==r['sha256'] for r in payload),'Packaged payload mutated'
    protected('T42');result=dict(status='PASS',exe=str(exe),payload_manifest=pkg['payload_manifest'],results=results,human_samples=0)
    write(out/'report.json',result);write(base/'latest_matrix.json',dict(status='PASS',report=str(out/'report.json')))
    print(json.dumps(dict(status='PASS',report=str(out/'report.json'),exe=str(exe),jobs=len(results))),flush=True)
if __name__=='__main__':main()
