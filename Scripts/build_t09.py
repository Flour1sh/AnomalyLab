"""Prepare/package T09 with standard Python and local UE AutomationTool.

No MCP, UI automation, gameplay launch, or source asset generation. Default is
preflight only; --package cooks and archives a Windows Development build.
"""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
from datetime import datetime, timezone

from prepare_t07 import PACKAGES

ROOT = Path(__file__).resolve().parent.parent
MAP = '/Game/Prototype/Maps/L_Prototype'


def inventory():
    result = []
    for package in PACKAGES:
        path = ROOT / 'Content' / (package + ('.umap' if package == MAP[6:] else '.uasset'))
        data = path.read_bytes() if path.is_file() else b''
        result.append(dict(package='/Game/' + package, size=len(data),
                           sha256=hashlib.sha256(data).hexdigest() if data else None))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', action='store_true')
    parser.add_argument('--engine', type=Path, default=Path('E:/UE_5.8'))
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    report_dir = ROOT / 'Saved/T09' / stamp
    report_dir.mkdir(parents=True, exist_ok=False)
    output = ROOT / 'Builds/T09' / stamp
    project = ROOT / (ROOT.name + '.uproject')
    # MSVC fails to create PCH output under this project's Unicode path.
    # Cook a real, independent snapshot; never hard-link mutable source assets.
    build_root = ROOT.parent / 'T09BuildWork' / stamp
    build_project = build_root / 'AnomalyLabT09.uproject'
    dotnet = args.engine / 'Engine/Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'
    uat = args.engine / 'Engine/Binaries/DotNET/AutomationTool/AutomationTool.dll'
    state = (ROOT / 'Docs/STATE.md').read_text(encoding='utf-8-sig')
    engine_ini = (ROOT / 'Config/DefaultEngine.ini').read_text(encoding='utf-8-sig')
    game_ini = (ROOT / 'Config/DefaultGame.ini').read_text(encoding='utf-8-sig')
    before = inventory()
    checks = {
        'T08 accepted': 'Last Completed Ticket: T08' in state,
        'T09 current': 'Current Ticket: T09' in state,
        '19 core packages present': all(a['size'] for a in before),
        'default map': f'GameDefaultMap={MAP}.L_Prototype' in engine_ini,
        'Development config': 'BuildConfiguration=PPBC_Development' in game_ini,
        'map included': f'+MapsToCook=(FilePath="{MAP}")' in game_ini,
        'project present': project.is_file(),
        'AutomationTool present': dotnet.is_file() and uat.is_file(),
    }
    command = [str(dotnet), str(uat), 'BuildCookRun', f'-project={build_project}',
               '-nop4', '-unattended', '-utf8output', '-nocompileeditor',
               f'-unrealexe={args.engine / "Engine/Binaries/Win64/UnrealEditor-Cmd.exe"}',
               '-platform=Win64', '-clientconfig=Development',
               '-build', '-ubtargs=-NoUBA', '-cook', f'-map={MAP}', '-stage', '-pak', '-iostore',
               '-package', '-archive', f'-archivedirectory={output}']
    report = dict(created_utc=stamp, checks=checks, source_assets=before,
                  preflight='PASS' if all(checks.values()) else 'FAIL',
                  packaging='NOT RUN', smoke_test='NOT RUN', PIE='NOT RUN',
                  uassets_created=[], command=command, output=str(output))
    report['build_snapshot'] = str(build_root)

    def save():
        data = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
        (report_dir / 'build.json').write_text(data, encoding='utf-8')
        (ROOT / 'Saved/T09/latest.json').write_text(data, encoding='utf-8')

    save()
    print(f"Preflight: {report['preflight']}; report: {report_dir}", flush=True)
    if not all(checks.values()):
        print(json.dumps(checks, ensure_ascii=False), flush=True)
        return 1
    if not args.package:
        return 0
    print(f'Copying source snapshot to {build_root}', flush=True)
    build_root.mkdir(parents=True, exist_ok=False)
    shutil.copy2(project, build_project)
    for folder in ('Config', 'Content', 'Plugins'):
        if (ROOT / folder).exists():
            shutil.copytree(ROOT / folder, build_root / folder)
    env = os.environ.copy()
    env['DOTNET_ROOT'] = str(dotnet.parent)
    env['DOTNET_MULTILEVEL_LOOKUP'] = '0'
    env['uebp_LogFolder'] = str(report_dir / 'UAT')
    report['packaging'] = 'RUNNING'
    save()
    log_path = report_dir / 'packaging.log'
    report['log'] = str(log_path)
    try:
        with log_path.open('wb') as log:
            process = subprocess.Popen(command, cwd=args.engine / 'Engine', env=env,
                                       stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            report['pid'] = process.pid
            save()
            print(f'Packaging PID {process.pid}; log: {log_path}', flush=True)
            code = process.wait()
        report['exit_code'] = code
        exes = list(output.rglob('*.exe')) if output.exists() else []
        containers = list(output.rglob('*.utoc')) if output.exists() else []
        report['executables'] = [str(p) for p in exes]
        report['containers'] = [str(p) for p in containers]
        report['source_assets_unchanged'] = before == inventory()
        log_text = log_path.read_text(encoding='utf-8', errors='replace')
        report['uat_success_marker'] = 'BUILD SUCCESSFUL' in log_text
        success = (code == 0 and bool(exes) and bool(containers)
                   and report['source_assets_unchanged'] and report['uat_success_marker'])
        report['packaging'] = 'PASS' if success else 'FAIL'
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save()
        print(f"Packaging: {report['packaging']}; smoke test NOT RUN; {output}", flush=True)
        return 0 if success else 1
    except OSError as exc:
        report['packaging'] = 'FAIL'
        report['error'] = str(exc)
        save()
        raise


if __name__ == '__main__':
    raise SystemExit(main())
