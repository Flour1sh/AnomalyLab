"""Only resize the existing scan hint for the separate resource line; no tree rebuild."""
import json,shutil
from pathlib import Path
from datetime import datetime
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'Saved/V04/T27'/('UI_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')); out.mkdir(parents=True)
src=ROOT/'Content/UI/WBP_ScanPanel.uasset'; shutil.copy2(src,out/src.name)
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem); U=unreal.get_default_object(unreal.UMGToolSet)
bp=A.load_asset('/Game/UI/WBP_ScanPanel')
w={str(x.widget.get_name()):x.widget for x in U.call_method('GetWidgets',(bp,)).widgets if x.widget}
hint=w['ScanHint']; hint.slot.set_size(unreal.Vector2D(1000,96)); hint.set_auto_wrap_text(True)
BlueprintTools.compile_blueprint(bp,warnings_as_errors=True)
assert A.save_loaded_asset(bp,only_if_is_dirty=False)
(out/'report.json').write_text(json.dumps(dict(status='PASS',changed=['Content/UI/WBP_ScanPanel.uasset'],hint_size=[1000,96]),indent=2),encoding='utf-8')
