"""New independent v0.5 Development package, strictly after T35–T41 gates."""
import json,hashlib
from pathlib import Path
from datetime import datetime
from cpp_migration import ROOT,ENGINE,build_snapshot,context,run_process
from package_payload import is_runtime_file
from checkpoint_v05 import sha,write
def main():
    evidence=ROOT/'Saved/V05/T42';evidence.mkdir(parents=True,exist_ok=True)
    for task in range(35,42):
        index=json.loads((ROOT/f'Saved/V05/checkpoint_T{task}_verified.json').read_text(encoding='utf-8'));assert index['status']=='PASS'
        gate=json.loads((ROOT/f'Saved/V05/T{task}/latest_gate.json').read_text(encoding='utf-8'));assert gate['status']=='PASS'
        assert json.loads(Path(gate['report']).read_text(encoding='utf-8'))['status']=='PASS'
    if (evidence/'package_report.json').exists():
        preflight=json.loads((evidence/'preflight_report.json').read_text(encoding='utf-8'));assert preflight['status']=='PASS'
        assert sha(ROOT/'Binaries/Win64/UnrealEditor-AnomalyLab.dll')==preflight['module_sha256']
        assert all(sha(ROOT/p)==h for p,h in json.loads(Path(preflight['source_manifest']).read_text(encoding='utf-8')).items()),'Source changed after fix preflight'
    run=context();work=build_snapshot(run);stamp=datetime.now().strftime('%Y%m%dT%H%M%S')
    out=ROOT/'Builds/v0.5'/('AnomalyLab_v05_RC_'+stamp);assert not out.exists()
    source={p.relative_to(ROOT).as_posix():sha(p) for folder in ('Source','Config','Content') for p in (ROOT/folder).rglob('*') if p.is_file()}
    manifest=evidence/('package_source_'+stamp+'.json');write(manifest,source)
    assert all(sha(work/name)==digest for name,digest in source.items())
    maps=['/Game/Prototype/Maps/L_MainMenu','/Game/Maps/L_Hub','/Game/Maps/L_Lab','/Game/Prototype/Maps/L_Prototype','/Game/Prototype/Maps/L_LegacyPrototype']
    cmd=[str(ENGINE/'Engine/Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),str(ENGINE/'Engine/Binaries/DotNET/AutomationTool/AutomationTool.dll'),
         'BuildCookRun',f'-project={work/"AnomalyLab.uproject"}','-nop4','-unattended','-utf8output','-nocompileeditor',
         '-platform=Win64','-clientconfig=Development','-build','-ubtargs=-gather -NoUBTMakefiles -NoUBA -MaxParallelActions=2',
         '-cook','-map='+'+'.join(maps),'-stage','-pak','-iostore','-package','-archive',f'-archivedirectory={out}','-ddc=InstalledNoZenLocalFallback']
    write(evidence/('package_command_'+stamp+'.json'),cmd);code,log=run_process(run,'v05-rc-package',cmd,work)
    exe=out/'Windows/AnomalyLab.exe';good=code==0 and exe.is_file()
    result=dict(status='PASS' if good else 'FAIL',stage='T42 engineering RC, HUMAN_PENDING',directory=str(out),exe=str(exe),log=str(log),source_manifest=str(manifest),source_files=len(source),maps=maps)
    if good:
        payload=[dict(path=p.relative_to(out/'Windows').as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted((out/'Windows').rglob('*')) if p.is_file() and not is_runtime_file(p.relative_to(out/'Windows'))]
        payload_path=evidence/('package_payload_'+stamp+'.json');write(payload_path,dict(files=payload));result['payload_manifest']=str(payload_path);result['payload_files']=len(payload)
        assert all(sha(ROOT/name)==digest for name,digest in source.items()),'Source changed during packaging'
        write(evidence/'package_report.json',result)
    write(evidence/('package_report_'+stamp+'.json'),result);print(json.dumps(result,ensure_ascii=True),flush=True)
    return 0 if good else 1
if __name__=='__main__':raise SystemExit(main())
