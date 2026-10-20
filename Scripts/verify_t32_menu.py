import json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[1];A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);U=unreal.get_default_object(unreal.UMGToolSet)
bp=A.load_asset('/Game/UI/Menu/WBP_MainMenu');w={str(x.widget.get_name()):x.widget for x in U.call_method('GetWidgets',(bp,)).widgets if x.widget};checks=[]
def check(name,ok):checks.append(dict(check=name,passed=bool(ok)));assert ok,name
check('Version is current','v0.4 RC' in str(w['Version'].get_text()))
check('Finite scan instructions','默认3次/种' in str(w['GuideAction3'].get_text()))
check('Preparation / decoy instructions','局内放诱饵' in str(w['GuideAction1'].get_text()))
check('Observer counterplay instructions','红眼保持距离' in str(w['GuideRule'].get_text()))
for name in ['StartButton','SettingsButton','GuideButton','QuitButton','GuideBackButton','MenuDesign','GuidePanel','SettingsPanel','QuitPanel','LoadingPanel']:check('Preserved '+name,name in w)
(ROOT/'Saved/V04/T32/menu_reload_report.json').write_text(json.dumps(dict(status='PASS',checks=checks),ensure_ascii=False,indent=2),encoding='utf-8')
