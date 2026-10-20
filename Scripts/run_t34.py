"""Fresh-process D3D12 map/input/navigation tests, no packaging or player save slots."""
import argparse,hashlib,json,os,struct,subprocess
from datetime import datetime
from pathlib import Path
from test_save_slots import new_slot,cleanup_slot
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['Hub','Lab','Menu'],required=True);p.add_argument('--width',type=int,default=1280);p.add_argument('--height',type=int,default=720);p.add_argument('--task',default='T34');p.add_argument('--exe',type=Path);a=p.parse_args()
    out=ROOT/'Saved/V05'/a.task/('Runtime_'+a.mode+'_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+f'_{a.width}x{a.height}');out.mkdir(parents=True)
    slot=new_slot('V05T34')
    if a.exe: assert a.exe.resolve().is_relative_to(ROOT) and a.exe.is_file() and a.exe.name=='AnomalyLab.exe'
    command=[str(a.exe)] if a.exe else ['E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe',str(ROOT/'我的项目3.uproject')]
    if a.mode!='Menu':command+=['/Game/Maps/L_'+a.mode]
    if a.mode=='Lab':command+=['-AnomalyV05InspectLevel'] # Explicit read-only map audit; normal direct Lab separately returns Hub.
    if not a.exe:command+=['-game','-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset','-DDC=InstalledNoZenLocalFallback',f'-LocalDataCachePath={ROOT/"Saved/CppMigration/DerivedDataCache"}']
    command+=['-AnomalyV05LevelSmoke',f'-T34Mode={a.mode}',f'-T34Evidence={out}',f'-AnomalySaveSlot={slot}',f'-abslog={out/"runtime.log"}',
      '-RenderOffscreen','-d3d12','-windowed','-ForceRes',f'-ResX={a.width}',f'-ResY={a.height}','-unattended','-nosound','-UTF8Output','-NoScreenMessages','-nosplash']
    (out/'command.json').write_text(json.dumps(command,ensure_ascii=False,indent=2),encoding='utf-8');print('T34 evidence '+str(out),flush=True)
    code=-1
    try:
        with (out/'stdout.log').open('wb') as f:
            proc=subprocess.Popen(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            try:code=proc.wait(timeout=210)
            except subprocess.TimeoutExpired:proc.kill();proc.wait();raise RuntimeError('Timed out '+str(out))
    finally:
        removed=cleanup_slot(slot,exe=a.exe);(out/'save_isolation.json').write_text(json.dumps(dict(slot=slot,removed=removed),indent=2),encoding='utf-8')
    report=json.loads((out/'report.json').read_text(encoding='utf-8-sig'));assert code==0 and report['status']=='PASS' and all(x['passed'] for x in report['checks']),str(out)
    expected={'Hub':['01_hub_panorama','02_hub_shop','03_hub_loadout','04_hub_departure','05_hub_report'],'Lab':['01_lab_entry','02_lab_A','03_lab_B','04_lab_C','05_lab_exit'],'Menu':['00_menu','01_menu_to_hub']}[a.mode]
    for name in expected:
        data=(out/(name+'.png')).read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[16:24])==(a.width,a.height),name
    result=dict(status='PASS',mode=a.mode,checks=len(report['checks']),frames=len(expected),resolution=[a.width,a.height],directory=str(out),human_samples=0,module_sha256=hashlib.sha256((a.exe or ROOT/'Binaries/Win64/UnrealEditor-AnomalyLab.dll').read_bytes()).hexdigest())
    (ROOT/'Saved/V05'/a.task/f'latest_{a.mode}_{a.height}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=True),flush=True)
if __name__=='__main__':main()
