"""Build a versioned Win64 Development RC, preserving all historical packages."""
import json, hashlib, shutil
from datetime import datetime
from pathlib import Path
from cpp_migration import ROOT, ENGINE, build_snapshot, context, run_process
run=context()
work=build_snapshot(run)
stamp=datetime.now().strftime('%Y%m%dT%H%M%S')
out=ROOT/'Builds/v0.3'/('AnomalyLab_RC_'+stamp)
tracked=[]
for folder in ['Source','Config','Content/UI','Content/Prototype/Data/Items','Content/Prototype/Audio','Content/Prototype/Maps','Content/Prototype/Environment/ScenePolish']:
    tracked.extend(p for p in (ROOT/folder).rglob('*') if p.is_file())
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}
manifest_path=ROOT/'Saved/V03'/('package_source_'+stamp+'.json')
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
for relative,sha in manifest.items():
    assert hashlib.sha256((work/relative).read_bytes()).hexdigest()==sha,relative
maps=['/Game/Prototype/Maps/L_MainMenu','/Game/Prototype/Maps/L_Prototype','/Game/Prototype/Maps/L_LegacyPrototype']
command=[str(ENGINE/'Engine/Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),
         str(ENGINE/'Engine/Binaries/DotNET/AutomationTool/AutomationTool.dll'),'BuildCookRun',f'-project={work/"AnomalyLab.uproject"}',
         '-nop4','-unattended','-utf8output','-nocompileeditor','-platform=Win64','-clientconfig=Development','-build',
         '-ubtargs=-gather -NoUBA -MaxParallelActions=1','-cook','-map='+'+'.join(maps),
         '-stage','-pak','-iostore','-package','-archive',f'-archivedirectory={out}','-ddc=InstalledNoZenLocalFallback']
code,log=run_process(run,'v03-package',command,work)
exe=out/'Windows/AnomalyLab.exe'
summary=dict(status='PASS' if code==0 and exe.exists() else 'FAIL',directory=str(out),exe=str(exe),log=str(log),
             source_manifest=str(manifest_path),source_files_verified=len(manifest),maps=maps)
report=ROOT/'Saved/V03/package_report.json'
if report.exists(): shutil.copy2(report,report.with_name('package_report_before_'+stamp+'.json'))
report.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True))
raise SystemExit(code if code else (0 if exe.exists() else 1))

