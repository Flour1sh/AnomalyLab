"""Isolated, explicitly opt-in v0.4 native boundary regressions."""
import argparse, json, subprocess
from pathlib import Path
from datetime import datetime
from test_save_slots import new_slot,validate_slot,cleanup_slot
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(); p.add_argument('--stage',default='T27'); p.add_argument('--exe',type=Path)
p.add_argument('--render',action='store_true'); p.add_argument('--width',type=int,default=1280); p.add_argument('--height',type=int,default=720)
p.add_argument('--save-case',default=''); p.add_argument('--slot'); p.add_argument('--keep-slot',action='store_true')
a=p.parse_args()
out=ROOT/'Saved/V04'/a.stage/'Runs'/(datetime.now().strftime('%Y%m%dT%H%M%S%f')+('_package' if a.exe else '_editor'))
out.mkdir(parents=True)
slot=validate_slot(a.slot or new_slot(a.stage))
cmd=[str(a.exe or Path('E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'))]
if not a.exe: cmd += [str(ROOT/'我的项目3.uproject')]
cmd += ['/Game/Prototype/Maps/L_Prototype']
if not a.exe: cmd += ['-game','-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset','-DDC=InstalledNoZenLocalFallback',f'-LocalDataCachePath={ROOT/"Saved/CppMigration/DerivedDataCache"}']
cmd += ['-AnomalyV04Smoke',f'-V04Stage={a.stage}',f'-V04Evidence={out}',f'-AnomalySaveSlot={slot}',f'-abslog={out/"runtime.log"}','-unattended','-nosound','-UTF8Output','-NoScreenMessages']
if a.save_case: cmd += [f'-V04SaveCase={a.save_case}']
cmd += ['-RenderOffscreen','-windowed','-ForceRes',f'-ResX={a.width}',f'-ResY={a.height}','-nosplash'] if a.render else ['-nullrhi']
(out/'command.json').write_text(json.dumps(cmd,ensure_ascii=False,indent=2),encoding='utf-8')
print('v0.4 evidence: '+str(out),flush=True)
code=-1
try:
    with (out/'stdout.log').open('wb') as f:
        proc=subprocess.Popen(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        try: code=proc.wait(timeout=180)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait(); raise RuntimeError('Timed out '+str(out))
finally:
    removed=[] if a.keep_slot and code==0 else cleanup_slot(slot,exe=a.exe)
    (out/'save_isolation.json').write_text(json.dumps(dict(slot=slot,retained=a.keep_slot and code==0,removed=removed),ensure_ascii=False,indent=2),encoding='utf-8')
report=json.loads((out/'report.json').read_text(encoding='utf-8-sig'))
if report.get('save_path') and not a.keep_slot: cleanup_slot(slot,report['save_path'],exe=a.exe) # validates reported path too
assert code==0 and report['status']=='PASS' and all(x['passed'] for x in report['checks']),str(out)
summary=dict(status='PASS',checks=len(report['checks']),directory=str(out),report=str(out/'report.json'))
(ROOT/'Saved/V04'/a.stage/'latest_native.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True))
