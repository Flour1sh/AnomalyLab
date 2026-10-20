"""Run the T14 command-line smoke actor on the real map without GUI or MCP."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = '/Game/Prototype/Maps/' + ('L_LegacyPrototype' if (ROOT / 'Content/Prototype/Maps/L_LegacyPrototype.umap').is_file() else 'L_Prototype')
ENGINE = Path('E:/UE_5.8')
OUT = ROOT / 'Saved/T14'
OUT.mkdir(parents=True, exist_ok=True)
REPORT = OUT / 'runtime_report.json'
LOG = OUT / 'runtime_editor.log'
STDOUT = OUT / 'runtime_stdout.log'
if REPORT.exists():
    REPORT.unlink()
command = [str(ENGINE / 'Engine/Binaries/Win64/UnrealEditor.exe'),
           str(ROOT / '我的项目3.uproject'), MAP, '-game',
           '-nullrhi', '-nosound', '-unattended', '-UTF8Output', '-AnomalyT14Smoke',
           '-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset',
           '-DDC=InstalledNoZenLocalFallback',
           f'-LocalDataCachePath={ROOT / "Saved/CppMigration/DerivedDataCache"}',
           f'-T14Report={REPORT}', f'-abslog={LOG}']
with STDOUT.open('wb') as stream:
    process = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    code = process.wait(timeout=120)
assert REPORT.is_file(), f'Missing T14 report; exit={code}, log={LOG}'
result = json.loads(REPORT.read_text(encoding='utf-8-sig'))
assert code == 0 and result['status'] == 'PASS' and all(check['passed'] for check in result['checks']), \
    f'T14 smoke failed; exit={code}, report={REPORT}, log={LOG}'
print(json.dumps(dict(status=result['status'], checks=len(result['checks']), report=str(REPORT), log=str(LOG)), ensure_ascii=False))
