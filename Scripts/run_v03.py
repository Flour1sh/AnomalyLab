"""Run the real exploration map: logic or offscreen rendered automation, no MCP/UI takeover."""
import argparse, json, subprocess
from pathlib import Path
from datetime import datetime
from test_save_slots import new_slot,cleanup_slot
ROOT = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser()
p.add_argument('--from-menu', action='store_true')
p.add_argument('--legacy-menu-route', action='store_true', help='Explicit old-map compatibility fixture; no production route override by default')
p.add_argument('--strategy', choices=['conservative','greedy','random'])
p.add_argument('--render', action='store_true')
p.add_argument('--width', type=int, default=1280)
p.add_argument('--height', type=int, default=720)
p.add_argument('--exe', type=Path)
p.add_argument('--mute', action='store_true')
args = p.parse_args()
out = ROOT/'Saved/V03/Runs'/(datetime.now().strftime('%Y%m%dT%H%M%S%f') + ('_render' if args.render else '_logic') + f'_{args.width}x{args.height}')
out.mkdir(parents=True)
slot=new_slot('V03')
exe = args.exe or Path('E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe')
command = [str(exe)]
if not args.exe:
    command += [str(ROOT/'我的项目3.uproject')]
if not args.from_menu: command += ['/Game/Prototype/Maps/L_Prototype']
if not args.exe:
    command += ['-game','-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset',
                '-DDC=InstalledNoZenLocalFallback',f'-LocalDataCachePath={ROOT/"Saved/CppMigration/DerivedDataCache"}']
if args.from_menu: command += ['-V03FromMenu',f'-MenuEvidence={out}']
if args.legacy_menu_route: command += ['-AnomalyLegacyMenuRoute']
if args.strategy: command += ['-V03Strategy='+args.strategy]
command += ['-AnomalyV03Smoke', f'-V03Evidence={out}',f'-AnomalySaveSlot={slot}', '-unattended','-UTF8Output','-NoScreenMessages',f'-abslog={out/"runtime.log"}']
if args.render:
    command += ['-V03Render','-RenderOffscreen','-windowed','-ForceRes',f'-ResX={args.width}',f'-ResY={args.height}','-nosplash']
else:
    command += ['-nullrhi','-nosound']
if args.mute and '-nosound' not in command: command.append('-nosound')
(out/'command.json').write_text(json.dumps(command,ensure_ascii=False,indent=2),encoding='utf-8')
print('V03 evidence: '+str(out),flush=True)
try:
    with (out/'stdout.log').open('wb') as stream:
        process = subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        try: code = process.wait(timeout=520)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(); raise RuntimeError('Timed out: '+str(out))
finally:
    removed=cleanup_slot(slot,exe=args.exe)
    (out/'save_isolation.json').write_text(json.dumps(dict(slot=slot,removed=removed),ensure_ascii=False,indent=2),encoding='utf-8')
path = out/'runtime_report.json'
assert path.exists(),f'Missing runtime report: exit={code}; {out}'
report = json.loads(path.read_text(encoding='utf-8-sig'))
assert code==0 and report['status']=='PASS' and all(c['passed'] for c in report['checks']),f'Failed: exit={code}; {out}'
if args.render and not args.strategy:
    assert len(list(out.glob('*.png'))) >= 12, 'Missing rendered evidence'
if args.from_menu:
    assert json.loads((out/'menu_boot_report.json').read_text(encoding='utf-8-sig'))['status']=='PASS'
summary = dict(status='PASS',from_menu=args.from_menu,target='package' if args.exe else 'editor-game',render=args.render,mute=args.mute,
               strategy=args.strategy,resolution=[args.width,args.height],checks=len(report['checks']),directory=str(out))
(ROOT/'Saved/V03'/('latest_'+(args.strategy+'_' if args.strategy else '')+('packaged_' if args.exe else '')+('render' if args.render else 'logic')+f'_{args.width}x{args.height}.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True))
