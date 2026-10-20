"""Run the T15 real-map gameplay checks headlessly, with MCP plugins disabled."""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = '/Game/Prototype/Maps/' + ('L_LegacyPrototype' if (ROOT / 'Content/Prototype/Maps/L_LegacyPrototype.umap').is_file() else 'L_Prototype')
ENGINE = Path('E:/UE_5.8')
OUT = ROOT / (sys.argv[1] if len(sys.argv) > 1 else 'Saved/T15')
OUT.mkdir(parents=True, exist_ok=True)
stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
REPORT = OUT / 'runtime_report.json'
LOG = OUT / f'runtime_{stamp}.log'
STDOUT = OUT / f'runtime_stdout_{stamp}.log'
if REPORT.exists():
    REPORT.rename(OUT / f'runtime_report_before_{stamp}.json')
command = [str(ENGINE / 'Engine/Binaries/Win64/UnrealEditor.exe'),
           str(ROOT / '我的项目3.uproject'), MAP, '-game',
           '-nullrhi', '-nosound', '-unattended', '-UTF8Output', '-AnomalyT15Smoke',
           '-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset',
           '-DDC=InstalledNoZenLocalFallback',
           f'-LocalDataCachePath={ROOT / "Saved/CppMigration/DerivedDataCache"}',
           f'-T15Report={REPORT}', f'-abslog={LOG}']
with STDOUT.open('wb') as stream:
    process = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        code = process.wait(timeout=150)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError(f'T15 smoke timed out; log={LOG}')
assert REPORT.is_file(), f'Missing T15 report; exit={code}, log={LOG}'
result = json.loads(REPORT.read_text(encoding='utf-8-sig'))
assert code == 0 and result['status'] == 'PASS' and all(c['passed'] for c in result['checks']), \
    f'T15 smoke failed; exit={code}, report={REPORT}, log={LOG}'
print(json.dumps(dict(status=result['status'], checks=len(result['checks']), report=str(REPORT), log=str(LOG)), ensure_ascii=False))
