"""Compile new materials with D3D12 and photograph the level without taking over a screen."""
from cpp_migration import ROOT,ENGINE,context,run_process
import json
out=ROOT/'Saved/ScenePolish/capture.log'
command=[str(ENGINE/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'),str(ROOT/'我的项目3.uproject'),
    f'-ExecutePythonScript={ROOT/"Scripts/capture_scene_polish.py"}',
    '-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset','-EnablePlugins=EditorToolset,PythonScriptPlugin,UMGToolSet',
    '-unattended','-RenderOffscreen','-d3d12','-nosound','-nosplash','-UTF8Output','-DDC=InstalledNoZenLocalFallback',
    f'-LocalDataCachePath={ROOT/"Saved/CppMigration/DerivedDataCache"}',f'-abslog={out}']
code,log=run_process(context(),'scene-capture',command)
assert code==0 and 'LogPython: Error:' not in out.read_text(encoding='utf-8',errors='replace')
assert json.loads((ROOT/'Saved/ScenePolish/capture_report.json').read_text(encoding='utf-8'))['status']=='PASS'
