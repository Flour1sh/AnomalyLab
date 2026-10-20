from pathlib import Path
from cpp_migration import ROOT, ENGINE, context, run_process
import json
run=context()
log=ROOT/'Saved/V03/material_warmup.log'
command=[str(ENGINE/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'),str(ROOT/'我的项目3.uproject'),
         f'-ExecutePythonScript={ROOT/"Scripts/warm_v03_materials.py"}',
         '-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset','-EnablePlugins=EditorToolset,PythonScriptPlugin,UMGToolSet',
         '-unattended','-RenderOffscreen','-d3d12','-nosound','-nosplash','-UTF8Output','-DDC=InstalledNoZenLocalFallback',
         f'-LocalDataCachePath={ROOT/"Saved/CppMigration/DerivedDataCache"}',f'-abslog={log}']
code,_=run_process(run,'v03-material-warmup',command)
assert code==0 and 'LogPython: Error:' not in log.read_text(encoding='utf-8',errors='replace')
assert json.loads((ROOT/'Saved/V03/material_warmup.json').read_text(encoding='utf-8'))['status']=='PASS'
