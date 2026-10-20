"""Normal default-menu launch: no gameplay automation flags, no test save slot."""
import argparse,json,subprocess,hashlib,os
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path);a=p.parse_args()
out=ROOT/'Saved/V04/T32'/('ColdBoot_'+datetime.now().strftime('%Y%m%dT%H%M%S%f'));out.mkdir(parents=True)
def player_saves():
    roots=[ROOT/'Saved/SaveGames',Path(os.environ['LOCALAPPDATA'])/'AnomalyLab/Saved/SaveGames']
    if a.exe:roots.append(a.exe.resolve().parent/'AnomalyLab/Saved/SaveGames')
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for r in roots for p in r.glob('AnomalyLab_Meta_v04.sav*') if p.is_file()}
before=player_saves()
cmd=[str(a.exe or Path('E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'))]
if not a.exe:cmd += [str(ROOT/'我的项目3.uproject'),'-game','-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset','-DDC=InstalledNoZenLocalFallback',f'-LocalDataCachePath={ROOT/"Saved/CppMigration/DerivedDataCache"}']
cmd += ['-seconds=12','-RenderOffscreen','-windowed','-ForceRes','-ResX=1280','-ResY=720','-unattended','-nosound','-UTF8Output',f'-abslog={out/"runtime.log"}']
(out/'command.json').write_text(json.dumps(cmd,ensure_ascii=False,indent=2),encoding='utf-8')
with (out/'stdout.log').open('wb') as f:code=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=100).returncode
log=(out/'runtime.log').read_text(encoding='utf-8',errors='replace');checks=[]
def check(name,ok):checks.append(dict(check=name,passed=bool(ok)))
check('Graceful engine time-limit exit',code==0)
check('Default menu actually ready','[MainMenu] Ready; Level01=/Game/Prototype/Maps/L_Prototype' in log and 'L_MainMenu' in log)
check('Normal default local slot loaded','Slot=AnomalyLab_Meta_v04 Test=0' in log)
check('No opt-in smoke driver ran',not any(x in log for x in ['[V03Smoke]','[ObserverSmoke]','[BalanceSmoke]','[T26Smoke]','[V04Smoke]','[MenuSmoke]']))
check('No gameplay run started','[Round] Round 1 spawned' not in log)
check('Existing player save bytes untouched',before==player_saves())
check('No gameplay fatal error','Fatal error:' not in log and 'LogTemp: Error:' not in log)
report=dict(status='PASS' if all(x['passed'] for x in checks) else 'FAIL',checks=checks,directory=str(out),scope='Default startup/menu/log verification without automation driver or input. Rendering enabled; human input/audio pending.')
(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=True));assert report['status']=='PASS',str(out)
