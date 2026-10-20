"""Run v0.2 fixed-seed statistics or full flow on Editor or packaged EXE."""
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('target', choices=['editor', 'packaged'])
parser.add_argument('suite', choices=['stats', 'flow', 'decision'])
parser.add_argument('--exe', type=Path, help='New Win64 package executable for regression')
parser.add_argument('--map', help='Map package override; editor defaults to the preserved Legacy map')
args = parser.parse_args()
map_package = args.map or ('/Game/Prototype/Maps/L_LegacyPrototype' if args.target == 'editor' and
    (root / 'Content/Prototype/Maps/L_LegacyPrototype.umap').is_file() else '/Game/Prototype/Maps/L_Prototype')
run = json.loads((root / 'Saved/CppMigration/latest.json').read_text(encoding='utf-8'))
out = root / 'Saved/T18'
out.mkdir(parents=True, exist_ok=True)
stem = f'{args.target}_{args.suite}'
stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
report = out / f'{stem}_report.json'
log = out / f'{stem}_{stamp}.log'
stdout = out / f'{stem}_{stamp}_stdout.log'
if report.exists():
    report.rename(out / f'{stem}_report_before_{stamp}.json')
if args.target == 'editor':
    exe = Path('E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe')
    command = [str(exe), str(root / '我的项目3.uproject'), map_package, '-game',
               '-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset',
               '-DDC=InstalledNoZenLocalFallback',
               f'-LocalDataCachePath={root / "Saved/CppMigration/DerivedDataCache"}']
else:
    exe = args.exe or root / 'Builds/CppMigration' / Path(run['directory']).name / 'Windows/AnomalyLab.exe'
    command = [str(exe), map_package]
assert exe.is_file(), exe
if args.suite == 'stats':
    command += ['-AnomalyMigrationSmoke', '-AnomalyStatsOnly', f'-MigrationReport={report}']
elif args.suite == 'decision':
    command += ['-AnomalyT14Smoke', f'-T14Report={report}']
else:
    command += ['-AnomalyT15Smoke', f'-T15Report={report}']
command += ['-nullrhi', '-nosound', '-unattended', '-UTF8Output', f'-abslog={log}']
with stdout.open('wb') as stream:
    process = subprocess.Popen(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        code = process.wait(timeout=180 if args.suite == 'flow' else 120)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError(f'{stem} timed out; log={log}')
assert report.is_file(), f'Missing report: {report}; exit={code}; log={log}'
result = json.loads(report.read_text(encoding='utf-8-sig'))
assert code == 0 and result['status'] == 'PASS' and all(c['passed'] for c in result['checks']), \
    f'{stem} failed; exit={code}; report={report}; log={log}'
print(json.dumps({'status': 'PASS', 'suite': stem, 'checks': len(result['checks']),
                  'report': str(report), 'log': str(log)}, ensure_ascii=False))
