"""Isolated, explicitly opt-in v0.4 native boundary regressions."""
import argparse, json, subprocess
from pathlib import Path
from datetime import datetime
from test_save_slots import new_slot,validate_slot,cleanup_slot
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(); p.add_argument('--stage',default='T31'); p.add_argument('--exe',type=Path)
p.add_argument('--render',action='store_true'); p.add_argument('--width',type=int,default=1280); p.add_argument('--height',type=int,default=720)
p.add_argument('--compare',type=Path); p.add_argument('--save-case',default=''); p.add_argument('--slot'); p.add_argument('--keep-slot',action='store_true')
a=p.parse_args()
out=ROOT/'Saved/V04'/a.stage/'Runs'/(datetime.now().strftime('%Y%m%dT%H%M%S%f')+('_package' if a.exe else '_editor'))
out.mkdir(parents=True)
slot=validate_slot(a.slot or new_slot(a.stage))
cmd=[str(a.exe or Path('E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'))]
if not a.exe: cmd += [str(ROOT/'我的项目3.uproject')]
cmd += ['/Game/Prototype/Maps/L_Prototype']
if not a.exe: cmd += ['-game','-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset','-DDC=InstalledNoZenLocalFallback',f'-LocalDataCachePath={ROOT/"Saved/CppMigration/DerivedDataCache"}']
cmd += ['-AnomalyBalanceSmoke',f'-T31Evidence={out}',f'-AnomalySaveSlot={slot}',f'-abslog={out/"runtime.log"}','-unattended','-nosound','-UTF8Output','-NoScreenMessages']
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
if a.compare:
    import math
    old=json.loads(a.compare.read_text(encoding='utf-8-sig'))
    assert old['logical_digest']==report['logical_digest'] and old['seed']==report['seed'] and old['runs_per_cell']==report['runs_per_cell'],'Simulation sequence mismatch'
    assert len(old['cells'])==len(report['cells'])
    for x,y in zip(old['cells'],report['cells']):
        assert x.keys()==y.keys()
        for k in x:
            assert math.isclose(x[k],y[k],rel_tol=1e-12,abs_tol=1e-12) if isinstance(x[k],float) else x[k]==y[k],k
    (out/'comparison.json').write_text(json.dumps(dict(status='PASS',source=str(a.compare),digest=report['logical_digest'],derived_float_tolerance=1e-12),indent=2),encoding='utf-8')
summary=dict(status='PASS' ,checks=len(report['checks']),directory=str(out),report=str(out/'report.json'))
(ROOT/'Saved/V04'/a.stage/'latest_balance.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True))
