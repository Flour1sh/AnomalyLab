"""Logged migration build/inspection driver. No UI, no old Blueprint generators."""
import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = Path('E:/UE_5.8')


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def context():
    return json.loads((ROOT/'Saved/CppMigration/latest.json').read_text(encoding='utf-8'))


def journal(run, event, **fields):
    with (Path(run['directory'])/'journal.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(dict(time=now(), event=event, **fields), ensure_ascii=False)+'\n')


def run_process(run, stage, command, cwd=None):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    log = Path(run['directory'])/(stage+'_'+stamp+'.log')
    journal(run, 'process_started', stage=stage, command=command, log=str(log))
    print(f'{stage}: log={log}', flush=True)
    with log.open('wb') as output:
        p = subprocess.Popen(command, cwd=cwd or ROOT, stdout=output, stderr=subprocess.STDOUT,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        journal(run, 'process_pid', stage=stage, pid=p.pid)
        code = p.wait()
    journal(run, 'process_finished', stage=stage, exit_code=code, log=str(log))
    print(f'{stage}: exit={code}', flush=True)
    return code, log


def copy_folder(source, destination):
    for path in source.rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts:
            continue
        target = destination/path.relative_to(source)
        if target.is_file() and target.stat().st_size == path.stat().st_size and target.stat().st_mtime_ns == path.stat().st_mtime_ns:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def build_snapshot(run):
    work = Path(run['build_workspace'])
    work.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT/'我的项目3.uproject', work/'AnomalyLab.uproject')
    for folder in ('Source', 'Config', 'Content', 'Plugins'):
        if (ROOT/folder).exists(): copy_folder(ROOT/folder, work/folder)
    return work


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare','build-editor','build-game','editor','package','smoke','smoke-editor'])
    parser.add_argument('--script')
    parser.add_argument('--phase', default='export')
    parser.add_argument('--map', help='Optional regression map override')
    args = parser.parse_args()
    if args.mode == 'prepare':
        backup = json.loads((ROOT/'Saved/P0/latest.json').read_text(encoding='utf-8'))
        manifest = json.loads(Path(backup['manifest']).read_text(encoding='utf-8'))
        assert manifest['status'] == 'PASS'
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        out = ROOT/'Saved/CppMigration'/stamp
        out.mkdir(parents=True, exist_ok=False)
        run = dict(directory=str(out), backup=backup['directory'], created_utc=now(),
                   build_workspace=str(ROOT.parent/'CppBuildWork'/stamp))
        write(ROOT/'Saved/CppMigration/latest.json', run)
        journal(run, 'migration_prepared', source_backup=backup['directory'], scope='M0-M2 existing gameplay, native box/wallet/coordinator/threat; retain Blueprint presentation')
        write(out/'baseline_manifest.json', manifest)
        print(json.dumps(run, ensure_ascii=True))
        return 0
    run = context()
    dotnet = str(ENGINE/'Engine/Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe')
    if args.mode.startswith('build-'):
        work = build_snapshot(run)
        target = 'AnomalyLabEditor' if args.mode == 'build-editor' else 'AnomalyLab'
        command = [dotnet, str(ENGINE/'Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll'), target,
                   'Win64','Development',f'-Project={work / "AnomalyLab.uproject"}', '-gather', '-NoUBTMakefiles', '-NoUBA', '-MaxParallelActions=2', '-NoHotReloadFromIDE',
                   f'-Log={Path(run["directory"]) / (args.mode+"_ubt.log")}']
        code, log = run_process(run, args.mode, command, work)
        if code: return code
        if args.mode == 'build-editor':
            source, dest = work/'Binaries/Win64', ROOT/'Binaries/Win64'
            dest.mkdir(parents=True, exist_ok=True)
            products = list(source.glob('UnrealEditor-AnomalyLab*')) + [source/'UnrealEditor.modules']
            assert products and all(p.is_file() for p in products)
            for path in products: shutil.copy2(path, dest/path.name)
            receipt = source/'AnomalyLabEditor.target'
            assert receipt.is_file()
            receipt_text = receipt.read_text(encoding='utf-8')
            assert '../../AnomalyLab.uproject' in receipt_text
            (dest/'AnomalyLabEditor.target').write_text(
                receipt_text.replace('../../AnomalyLab.uproject', '../../我的项目3.uproject'), encoding='utf-8')
            journal(run, 'editor_module_deployed', files=[str(p.name) for p in products]+['AnomalyLabEditor.target'])
        return 0
    if args.mode == 'editor':
        assert args.script
        run['asset_phase'] = args.phase
        write(ROOT/'Saved/CppMigration/latest.json', run)
        script = (ROOT/'Scripts'/args.script).resolve()
        assert script.is_file() and script.is_relative_to(ROOT/'Scripts')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        engine_log = Path(run['directory'])/('ue_'+script.stem+'_'+stamp+'.log')
        command = [str(ENGINE/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'),str(ROOT/'我的项目3.uproject'),
                   f'-ExecutePythonScript={script}', '-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset',
                   '-EnablePlugins=EditorToolset,PythonScriptPlugin,UMGToolSet','-unattended','-nosplash','-nullrhi',
                   '-RenderOffscreen','-nosound','-UTF8Output','-DDC=InstalledNoZenLocalFallback',
                   f'-LocalDataCachePath={ROOT / "Saved/CppMigration/DerivedDataCache"}',f'-abslog={engine_log}']
        code, log = run_process(run, script.stem, command)
        text = engine_log.read_text(encoding='utf-8', errors='replace') if engine_log.exists() else ''
        if 'LogPython: Error:' in text or '[MIGRATION] FAIL' in text: return 1
        return code
    if args.mode == 'package':
        work = build_snapshot(run)
        output = ROOT/'Builds/CppMigration'/Path(run['directory']).name
        command = [dotnet,str(ENGINE/'Engine/Binaries/DotNET/AutomationTool/AutomationTool.dll'), 'BuildCookRun',
                   f'-project={work / "AnomalyLab.uproject"}','-nop4','-unattended','-utf8output','-nocompileeditor',
                   '-platform=Win64','-clientconfig=Development','-build','-ubtargs=-NoUBA -MaxParallelActions=2','-cook',
                   '-map=/Game/Prototype/Maps/L_MainMenu+/Game/Prototype/Maps/L_Prototype' +
                   ('+/Game/Prototype/Maps/L_LegacyPrototype' if (ROOT/'Content/Prototype/Maps/L_LegacyPrototype.umap').exists() else ''),
                   '-stage','-pak','-iostore','-package','-archive',
                   f'-archivedirectory={output}','-ddc=InstalledNoZenLocalFallback']
        return run_process(run, 'package', command, work)[0]
    if args.mode in ('smoke','smoke-editor'):
        editor_smoke = args.mode == 'smoke-editor'
        output = ROOT if editor_smoke else ROOT/'Builds/CppMigration'/Path(run['directory']).name/'Windows'
        exe = ENGINE/'Engine/Binaries/Win64/UnrealEditor.exe' if editor_smoke else output/'AnomalyLab.exe'
        assert exe.is_file(), exe
        report = Path(run['directory'])/('editor_runtime.json' if editor_smoke else 'packaged_runtime.json')
        command = [str(exe)]
        map_package = args.map or ('/Game/Prototype/Maps/L_LegacyPrototype' if editor_smoke and
            (ROOT/'Content/Prototype/Maps/L_LegacyPrototype.umap').exists() else '/Game/Prototype/Maps/L_Prototype')
        if editor_smoke:
            command += [str(ROOT/'我的项目3.uproject'),map_package,'-game','-DDC=InstalledNoZenLocalFallback',
                        f'-LocalDataCachePath={ROOT / "Saved/CppMigration/DerivedDataCache"}']
        else:
            command += [map_package]
        command += ['-nullrhi','-nosound','-unattended','-UTF8Output','-AnomalyMigrationSmoke',
                   f'-MigrationReport={report}',f'-abslog={Path(run["directory"])/("editor_game.log" if editor_smoke else "packaged_game.log")}']
        code, _ = run_process(run, 'editor_smoke' if editor_smoke else 'packaged_smoke', command, output)
        if code: return code
        if not report.is_file():
            journal(run,'packaged_smoke_missing_report',report=str(report));return 1
        result=json.loads(report.read_text(encoding='utf-8-sig'))
        passed=result.get('status')=='PASS' and all(item.get('passed') is True for item in result.get('checks',[]))
        journal(run,'packaged_smoke_report',status=result.get('status'),checks=len(result.get('checks',[])),passed=passed)
        return 0 if passed else 1
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
