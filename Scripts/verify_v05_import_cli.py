"""Actual production startup import (no Smoke flags), in a unique Automation_ target."""
import argparse,json,subprocess
from pathlib import Path
from datetime import datetime
from checkpoint_v05 import ROOT,sha,write
from test_save_slots import new_slot,cleanup_slot
def main():
    p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,required=True);a=p.parse_args();exe=a.exe.resolve();assert exe.is_relative_to(ROOT) and exe.is_file()
    base=ROOT/'Saved/V05/T42';fixture=json.loads((base/'latest_Import.json').read_text(encoding='utf-8'));source=Path(fixture['directory'])/'Automation_v04_fixture.sav';assert source.is_file()
    digest=sha(source);slot=new_slot('T42ImportCLI');out=base/('ImportCLI_'+datetime.now().strftime('%Y%m%dT%H%M%S'));out.mkdir();results=[]
    try:
        for i in range(2):
            log=out/f'boot_{i}.log';cmd=[str(exe),f'-AnomalySaveSlot={slot}',f'-AnomalyImportSave={source}','-ExecCmds=Quit','-unattended','-nullrhi','-nosound','-UTF8Output',f'-abslog={log}'];write(out/f'command_{i}.json',cmd)
            with (out/f'stdout_{i}.log').open('wb') as stream:code=subprocess.run(cmd,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=120).returncode
            text=log.read_text(encoding='utf-8',errors='replace');meta=[line for line in text.splitlines() if '[MetaSave] Slot=' in line]
            assert code==0 and len(meta)==1 and 'Test=0' in meta[0] and 'Balance=12345' in meta[0],str(log)
            if i==0:assert '已导入旧档' in meta[0]
            assert sha(source)==digest
            path=exe.parent/'AnomalyLab/Saved/SaveGames'/(slot+'.sav');assert path.is_file()
            if i==0:target_sha=sha(path)
            else:assert sha(path)==target_sha,'Repeated import overwrote destination'
            results.append(dict(status='PASS',log=str(log),meta=meta[0],target_sha256=target_sha))
    finally:removed=cleanup_slot(slot,exe=exe)
    result=dict(status='PASS',results=results,source_sha256=digest,source_unchanged=True,target_cleanup=removed,human_samples=0,scope='Normal production startup twice without Smoke flags, unique explicit Automation_ destination; no player save imported.')
    write(out/'report.json',result);print(json.dumps(dict(status='PASS',report=str(out/'report.json'),directory=str(out))),flush=True)
if __name__=='__main__':main()
