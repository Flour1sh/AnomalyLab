"""Exercise default boot, real rendered UMG, menu input and Level01 travel."""
from test_save_slots import new_slot,cleanup_slot
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--width', type=int, default=1280)
parser.add_argument('--height', type=int, default=720)
parser.add_argument('--legacy-menu-route', action='store_true', help='Explicit v0.4 menu fixture; T34 production route has a separate native test')
parser.add_argument('--exe', type=Path, help='Optional newly packaged AnomalyLab.exe')
args = parser.parse_args()
slot=new_slot("Menu")
out = ROOT / 'Saved/T19Menu/RenderRuns' / (datetime.now().strftime('%Y%m%dT%H%M%S') + f'_{args.width}x{args.height}')
out.mkdir(parents=True)
exe = args.exe or Path('E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe')
command = [str(exe)]
if not args.exe:
    command += [str(ROOT / '我的项目3.uproject'), '-game',
                '-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset',
                '-DDC=InstalledNoZenLocalFallback',
                f'-LocalDataCachePath={ROOT / "Saved/CppMigration/DerivedDataCache"}']
command += ['-RenderOffscreen', '-windowed', '-ForceRes', f'-ResX={args.width}', f'-ResY={args.height}',
            f'-AnomalySaveSlot={slot}', '-NoScreenMessages', '-nosplash', '-unattended', '-UTF8Output', '-AnomalyMenuSmoke',
            f'-MenuEvidence={out}', f'-abslog={out / "runtime.log"}']
if args.legacy_menu_route: command += ['-AnomalyLegacyMenuRoute']
(out / 'command.json').write_text(json.dumps(command, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Menu runtime evidence: {out}', flush=True)
try:
    with (out / 'stdout.log').open('wb') as stream:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            code = process.wait(timeout=190)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise RuntimeError(f'Menu timed out; {out}')
finally:
    cleanup_slot(slot,exe=args.exe)
report_path = out / 'runtime_report.json'
assert report_path.is_file(), f'Missing report; exit={code}; {out}'
report = json.loads(report_path.read_text(encoding='utf-8-sig'))
assert code == 0 and report['status'] == 'PASS', f'Menu failed; exit={code}; {out}'
for name in ('01_main_menu', '02_settings', '03_field_guide', '04_quit_confirmation', '05_level01'):
    assert (out / (name + '.png')).is_file(), f'Missing rendered screenshot: {name}; {out}'
summary = dict(status='PASS', target='packaged' if args.exe else 'editor-game',
               resolution=[args.width, args.height], checks=len(report['checks']), directory=str(out))
(ROOT / f'Saved/T19Menu/latest_{args.width}x{args.height}.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=True))
