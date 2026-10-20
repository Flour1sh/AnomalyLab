"""Fresh-process v0.5 actual travel tests; only isolated Automation_ saves."""
import argparse, hashlib, json, subprocess, os, re, shutil
from datetime import datetime
from pathlib import Path
from test_save_slots import new_slot, validate_slot, cleanup_slot
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--task',default='T35'); p.add_argument('--mode',default='Loop')
    p.add_argument('--exe',type=Path); p.add_argument('--slot'); p.add_argument('--keep-slot',action='store_true')
    p.add_argument('--render',action='store_true'); p.add_argument('--width',type=int,default=1280); p.add_argument('--height',type=int,default=720)
    p.add_argument('--no-telemetry',action='store_true')
    a=p.parse_args(); out=ROOT/'Saved/V05'/a.task/('Run_'+a.mode+'_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')); out.mkdir(parents=True)
    slot=validate_slot(a.slot or new_slot('V05'+a.task))
    corrupt={}
    if a.mode=='Corrupt':
        save_folder=(a.exe.parent/'AnomalyLab/Saved/SaveGames') if a.exe else ROOT/'Saved/SaveGames'
        save_folder.mkdir(parents=True,exist_ok=True)
        for suffix,payload in [('.sav',b'Explicit broken primary fixture'),('.sav.bak',b'Explicit broken backup fixture')]:
            path=save_folder/(slot+suffix); assert not path.exists();path.write_bytes(payload);corrupt[str(path)]=payload
    cmd=[str(a.exe or Path('E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'))]
    if not a.exe: cmd += [str(ROOT/'我的项目3.uproject')]
    if a.mode!='Journey': cmd += ['/Game/Maps/L_Lab' if a.mode=='Direct' else '/Game/Maps/L_Hub']
    if not a.exe: cmd += ['-game','-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset','-DDC=InstalledNoZenLocalFallback',f'-LocalDataCachePath={ROOT/"Saved/CppMigration/DerivedDataCache"}']
    cmd += ['-AnomalyV05Smoke',f'-V05Mode={a.mode}',f'-V05Evidence={out}',f'-AnomalySaveSlot={slot}',f'-abslog={out/"runtime.log"}','-unattended','-nosound','-UTF8Output','-NoScreenMessages']
    if a.no_telemetry:cmd+=['-NoRunTelemetry']
    cmd += ['-RenderOffscreen','-d3d12','-windowed','-ForceRes',f'-ResX={a.width}',f'-ResY={a.height}','-nosplash'] if a.render else ['-nullrhi']
    (out/'command.json').write_text(json.dumps(cmd,ensure_ascii=False,indent=2),encoding='utf-8'); print('V05 evidence: '+str(out),flush=True)
    code=-1
    try:
        with (out/'stdout.log').open('wb') as stream:
            proc=subprocess.Popen(cmd,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            try: code=proc.wait(timeout=360)
            except subprocess.TimeoutExpired: proc.kill();proc.wait();raise RuntimeError('Timed out '+str(out))
    finally:
        unchanged=all(Path(path).read_bytes()==payload for path,payload in corrupt.items())
        removed=[] if a.keep_slot and code==0 else cleanup_slot(slot,exe=a.exe)
        (out/'save_isolation.json').write_text(json.dumps(dict(slot=slot,retained=a.keep_slot and code==0,removed=removed,corrupt_fixture_unchanged=unchanged),indent=2),encoding='utf-8')
        assert unchanged,'Unreadable existing files were overwritten'
    report=json.loads((out/'report.json').read_text(encoding='utf-8-sig'))
    assert code==0 and report['status']=='PASS' and all(c['passed'] for c in report['checks']),str(out)
    telemetry=[]
    if int(a.task[1:])>=41:
        paths=re.findall(r'\[Telemetry\].*?Saved=1 .*?Path=([^\r\n]+)',(out/'runtime.log').read_text(encoding='utf-8',errors='replace'))
        for name in dict.fromkeys(paths):
            path=Path(name.strip()).resolve()
            assert re.fullmatch(r'[A-Fa-f0-9]{32}\.json',path.name) and path.parent.name=='Telemetry' and path.is_relative_to(ROOT),str(path)
            data=json.loads(path.read_text(encoding='utf-8-sig'))
            required=['RunId','Seed','EntryTime','ExitTime','Duration','Outcome','Room','ScansUsed','LootValue','CashExtracted','UpgradeLoadout','ThreatType','ThreatDamage','ReturnRouteTime','FPS','FrameSamples','Events','LabLoadSeconds']
            assert all(k in data for k in required) and len(data['Events'])<=512 and 0<data['FrameSamples']<=12000 and path.stat().st_size<=1024*1024,str(path)
            assert data['CashExtracted']+data['CarryLost']==data['LootValue'] and data['Duration']>=0
            if data['Outcome']!='Interrupted':assert data['HubLoadSeconds']>=.25,str(path)
            if data['Outcome'] in ['Failed','Error']:assert data['CashExtracted']==0 and not data['DurableCredit']
            if a.mode=='Journey':assert data['ScansUsed']==1 and len(data['Room'])>=2 and any(e['Kind']=='BoxSpawnPoint' for e in data['Events'])
            if a.mode=='RestartWrite':assert data['Outcome']=='Interrupted' and data['CarryLost']==123 and data['CashExtracted']==0
            dest=out/'telemetry'/path.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(path,dest)
            assert hashlib.sha256(dest.read_bytes()).digest()==hashlib.sha256(path.read_bytes()).digest()
            telemetry.append(str(dest))
        expected=report['completed_trips']+(1 if a.mode=='RestartWrite' else 0)
        assert len(telemetry)==(0 if a.no_telemetry else expected),f'Telemetry/trip mismatch: {out}'
    summary=dict(status='PASS',task=a.task,mode=a.mode,checks=len(report['checks']),trips=report['completed_trips'],report=str(out/'report.json'),directory=str(out),slot=slot,human_samples=0,
                 module_sha256=hashlib.sha256((a.exe if a.exe else ROOT/'Binaries/Win64/UnrealEditor-AnomalyLab.dll').read_bytes()).hexdigest(),telemetry=telemetry,telemetry_disabled=a.no_telemetry,resolution=[a.width,a.height] if a.render else None)
    (ROOT/'Saved/V05'/a.task/f'latest_{a.mode}.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=True),flush=True)
    if a.render:(ROOT/'Saved/V05'/a.task/f'latest_{a.mode}_{a.height}.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')

if __name__=='__main__':main()
