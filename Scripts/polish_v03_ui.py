"""Small contrast fix found during rendered inspection; no gameplay data changes."""
import unreal, shutil, json
from pathlib import Path
from datetime import datetime
from editor_toolset.toolsets.blueprint import BlueprintTools
ROOT=Path(__file__).resolve().parent.parent
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
U=unreal.get_default_object(unreal.UMGToolSet)
file=ROOT/'Content/UI/WBP_ExplorationPrompt.uasset'
backup=ROOT/'Saved/V03'/('T25UIBefore_'+datetime.now().strftime('%Y%m%dT%H%M%S%f'))
backup.mkdir(parents=True)
shutil.copy2(file,backup/file.name)
bp=A.load_asset('/Game/UI/WBP_ExplorationPrompt')
widgets={str(w.widget.get_name()):w.widget for w in U.call_method('GetWidgets',(bp,)).widgets if w.widget}
for name,y,width in [('PromptBacking',46,740),('NoticeBacking',126,820)]:
    if name in widgets: continue
    item=U.call_method('AddWidget',(bp,unreal.Image.static_class(),name,widgets['ExplorationCanvas'],-1))
    item.widget.set_color_and_opacity(unreal.LinearColor(.008,.02,.015,.86))
    item.widget.set_visibility(unreal.SlateVisibility.COLLAPSED)
    item.slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(.5,.5),maximum=unreal.Vector2D(.5,.5)))
    item.slot.set_position(unreal.Vector2D(0,y)); item.slot.set_alignment(unreal.Vector2D(.5,0)); item.slot.set_size(unreal.Vector2D(width,50))
    item.slot.set_z_order(-1)
BlueprintTools.compile_blueprint(bp,warnings_as_errors=True)
assert bp.get_editor_property('status')==unreal.BlueprintStatus.BS_UP_TO_DATE
assert A.save_loaded_asset(bp,only_if_is_dirty=False)
(ROOT/'Saved/V03/ui_polish.json').write_text(json.dumps(dict(status='PASS',backup=str(backup)),indent=2),encoding='utf-8')
