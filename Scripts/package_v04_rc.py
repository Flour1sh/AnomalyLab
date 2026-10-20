"""Independent v0.4 engineering RC package, preserving v0.3 packages/reports and all past candidates."""
import json,hashlib
from pathlib import Path
from datetime import datetime
from cpp_migration import ROOT,ENGINE,build_snapshot,context,run_process
run=context(); work=build_snapshot(run)
stamp=datetime.now().strftime('%Y%m%dT%H%M%S')
out=ROOT/'Builds/v0.4'/('AnomalyLab_v04_RC_'+stamp)
manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
          for folder in ('Source','Config','Content') for p in (ROOT/folder).rglob('*') if p.is_file()}
evidence=ROOT/'Saved/V04/T32'; evidence.mkdir(parents=True,exist_ok=True)
source=evidence/('package_source_'+stamp+'.json')
source.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
assert all(hashlib.sha256((work/name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
maps=['/Game/Prototype/Maps/L_MainMenu','/Game/Prototype/Maps/L_Prototype','/Game/Prototype/Maps/L_LegacyPrototype']
cmd=[str(ENGINE/'Engine/Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe'),str(ENGINE/'Engine/Binaries/DotNET/AutomationTool/AutomationTool.dll'),
    'BuildCookRun',f'-project={work/"AnomalyLab.uproject"}','-nop4','-unattended','-utf8output','-nocompileeditor',
    '-platform=Win64','-clientconfig=Development','-build','-ubtargs=-gather -NoUBTMakefiles -NoUBA -MaxParallelActions=1',
    '-cook','-map='+'+'.join(maps),'-stage','-pak','-iostore','-package','-archive',f'-archivedirectory={out}','-ddc=InstalledNoZenLocalFallback']
code,log=run_process(run,'v04-rc-package',cmd,work)
exe=out/'Windows/AnomalyLab.exe'
result=dict(status='PASS' if code==0 and exe.is_file() else 'FAIL',stage='T32 engineering RC, HUMAN_PENDING',directory=str(out),exe=str(exe),log=str(log),source_manifest=str(source),source_files=len(manifest))
(evidence/('package_report_'+stamp+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if code==0 and exe.is_file(): (evidence/'package_report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True)); raise SystemExit(code if code else (0 if exe.is_file() else 1))
