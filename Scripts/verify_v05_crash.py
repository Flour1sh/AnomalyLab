"""Actual OS process-tree termination at uncredited/credited boundaries; isolated saves only."""
import argparse,json,subprocess,time,re,os
from pathlib import Path
from datetime import datetime
from checkpoint_v05 import ROOT,sha,write
from test_save_slots import new_slot,cleanup_slot
def main():
    p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,required=True);a=p.parse_args();exe=a.exe.resolve();assert exe.is_relative_to(ROOT) and exe.is_file()
    out=ROOT/'Saved/V05/T42'/('Crash_'+datetime.now().strftime('%Y%m%dT%H%M%S'));out.mkdir();results=[]
    for case in ['carry_uncredited','credit_before_hub']:
        directory=out/case;directory.mkdir();slot=new_slot('T42Crash');log=directory/'runtime.log';proc=None
        command=[str(exe),'-AnomalyV05Smoke','-V05Mode=Journey',f'-V05Evidence={directory}',f'-AnomalySaveSlot={slot}',f'-abslog={log}','-FORCELOGFLUSH','-RenderOffscreen','-d3d12','-windowed','-ForceRes','-ResX=1280','-ResY=720','-unattended','-nosound','-UTF8Output','-NoScreenMessages']
        write(directory/'command.json',command);print('START crash '+case,flush=True)
        try:
            with (directory/'stdout.log').open('wb') as stream:
                proc=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                deadline=time.monotonic()+180;triggered=False
                while time.monotonic()<deadline and proc.poll() is None:
                    text=log.read_text(encoding='utf-8',errors='replace') if log.exists() else ''
                    assert '[Journey] FAIL' not in text,str(log)
                    marker='[Journey] PASS Actual E pickup carries real generated value without credit' if case=='carry_uncredited' else 'Phase=3->4'
                    if marker in text:
                        killed=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
                        (directory/'taskkill.log').write_bytes(killed.stdout+killed.stderr);assert killed.returncode==0,str(directory)
                        proc.wait(timeout=20);triggered=True;break
                    time.sleep(.01)
                assert triggered,'Crash boundary not reached: '+str(directory)
            text=log.read_text(encoding='utf-8',errors='replace');assert not (directory/'report.json').exists(),'Journey finished instead of abrupt termination'
            save=exe.parent/'AnomalyLab/Saved/SaveGames'/(slot+'.sav');assert save.is_file();before=sha(save)
            if case=='carry_uncredited':
                assert 'Phase=3->4' not in text;balance=4400
            else:
                rewards=re.findall(r'\[Box\] Outcome=0 Reward=(\d+)',text)
                assert len(rewards)==1 and int(rewards[0])>0 and '[Round] Run Ended Error=0' in text
                balance=4400+int(rewards[0]) # Expected credit comes from actual generated loot, not telemetry.
                assert not re.search(r'Phase=4->0',text[text.index('Phase=3->4'):]),'Hub already acknowledged'
                paths=re.findall(r'\[Telemetry\].*?Saved=1 .*?Path=([^\r\n]+)',text)
                if paths:
                    for attempt in range(50):
                        try:
                            telemetry=json.loads(Path(paths[-1].strip()).read_text(encoding='utf-8'))
                            write(directory/'committed_telemetry.json',telemetry);break
                        except (OSError,ValueError):time.sleep(.1)
            restart=directory/'restart';restart.mkdir();restartlog=restart/'runtime.log'
            cmd=[str(exe),'-AnomalyV05LevelSmoke','-T34Mode=Menu',f'-T34Evidence={restart}',f'-AnomalySaveSlot={slot}',f'-abslog={restartlog}','-RenderOffscreen','-d3d12','-windowed','-ForceRes','-ResX=1280','-ResY=720','-unattended','-nosound','-UTF8Output','-NoScreenMessages'];write(restart/'command.json',cmd)
            with (restart/'stdout.log').open('wb') as stream:code=subprocess.run(cmd,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=180).returncode
            report=json.loads((restart/'report.json').read_text(encoding='utf-8-sig'));assert code==0 and report['status']=='PASS' and all(r['passed'] for r in report['checks'])
            meta=[s for s in restartlog.read_text(encoding='utf-8',errors='replace').splitlines() if '[MetaSave] Slot=' in s];assert len(meta)==1 and f'Balance={balance}' in meta[0]
            assert sha(save)==before,'Restart credited/replayed/mutated progress'
            results.append(dict(case=case,status='PASS',process_pid=proc.pid,abrupt_tree_kill=True,permanent_balance=balance,save_sha256=before,restart_report=str(restart/'report.json'),directory=str(directory)))
        finally:
            if proc is not None and proc.poll() is None:subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);proc.wait(timeout=20)
            cleanup_slot(slot,exe=exe)
    result=dict(status='PASS',results=results,human_samples=0,scope='Actual task-owned Windows process trees killed after real synthetic pickup or durable credit before Hub ack; normal default-menu restart, exact save hash unchanged.')
    write(out/'report.json',result);print(json.dumps(dict(status='PASS',report=str(out/'report.json'),directory=str(out))),flush=True)
if __name__=='__main__':main()
