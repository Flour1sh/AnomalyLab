"""Archive the menu-enabled Win64 Development build without overwriting v0.2."""
import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from cpp_migration import ROOT, ENGINE, build_snapshot, context, run_process

run = context()
work = build_snapshot(run)
stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
out = ROOT / 'Builds/v0.3' / ('T19Menu_' + stamp)
tracked = list((ROOT / 'Source').rglob('*')) + list((ROOT / 'Content/UI/Menu').rglob('*.uasset'))
tracked += [ROOT / 'Config/DefaultEngine.ini', ROOT / 'Config/DefaultGame.ini',
            ROOT / 'Content/Prototype/Maps/L_MainMenu.umap', ROOT / 'Content/Prototype/Maps/L_Prototype.umap']
manifest = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked if path.is_file()}
manifest_path = ROOT / 'Saved/T19Menu' / ('package_source_' + stamp + '.json')
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
for relative, digest in manifest.items():
    assert hashlib.sha256((work / relative).read_bytes()).hexdigest() == digest, relative
dotnet = ENGINE / 'Engine/Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'
command = [str(dotnet), str(ENGINE / 'Engine/Binaries/DotNET/AutomationTool/AutomationTool.dll'),
           'BuildCookRun', f'-project={work / "AnomalyLab.uproject"}', '-nop4', '-unattended', '-utf8output',
           '-nocompileeditor', '-platform=Win64', '-clientconfig=Development', '-build',
           '-ubtargs=-gather -NoUBA -MaxParallelActions=4', '-cook',
           '-map=/Game/Prototype/Maps/L_MainMenu+/Game/Prototype/Maps/L_Prototype',
           '-stage', '-pak', '-iostore', '-package', '-archive', f'-archivedirectory={out}',
           '-ddc=InstalledNoZenLocalFallback']
code, log = run_process(run, 't19-menu-package', command, work)
summary = dict(status='PASS' if code == 0 else 'FAIL', directory=str(out), log=str(log),
               exe=str(out / 'Windows/AnomalyLab.exe'), maps=['L_MainMenu', 'L_Prototype'],
               source_manifest=str(manifest_path), source_files_verified=len(manifest))
previous = ROOT / 'Saved/T19Menu/package_report.json'
if previous.is_file():
    shutil.copy2(previous, previous.with_name('package_report_before_' + stamp + '.json'))
(ROOT / 'Saved/T19Menu/package_report.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
raise SystemExit(code)
