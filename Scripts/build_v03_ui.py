"""T22: passive inventory HUD; only rebuild the exploration widget."""
from pathlib import Path
from datetime import datetime
import json
import shutil
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'Saved/V03'
A = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
U = unreal.get_default_object(unreal.UMGToolSet)
file = ROOT/'Content/UI/WBP_ExplorationPrompt.uasset'
backup = OUT/('T22AssetsBefore_' + datetime.now().strftime('%Y%m%dT%H%M%S%f'))
backup.mkdir(parents=True)
shutil.copy2(file, backup/file.name)
bp = A.load_asset('/Game/UI/WBP_ExplorationPrompt')
tree = U.call_method('GetWidgets', (bp,)).widgets
if tree:
    assert U.call_method('RemoveWidget', (bp, tree[0].widget))
root = U.call_method('AddWidget', (bp, unreal.CanvasPanel.static_class(), 'ExplorationCanvas', None, -1)).widget
for name, anchor, position, size, align, font, justify in (
    ('InteractionPrompt', (.5,.5), (0,50), (680,36), (.5,0), 20, unreal.TextJustify.CENTER),
    ('ExplorationObjective', (1,0), (-24,115), (460,125), (1,0), 18, unreal.TextJustify.RIGHT),
    ('InventoryText', (1,0), (-24,255), (410,210), (1,0), 18, unreal.TextJustify.RIGHT),
    ('NoticeText', (.5,.5), (0,130), (750,50), (.5,0), 22, unreal.TextJustify.CENTER)):
    item = U.call_method('AddWidget', (bp, unreal.TextBlock.static_class(), name, root, -1))
    item.widget.set_text(unreal.Text(''))
    item.widget.set_font_size(font)
    item.widget.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(.78,.95,.87,1)))
    item.widget.set_shadow_offset(unreal.Vector2D(1,1))
    item.widget.set_shadow_color_and_opacity(unreal.LinearColor(0,0,0,1))
    item.widget.set_editor_property('justification', justify)
    item.slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(*anchor), maximum=unreal.Vector2D(*anchor)))
    item.slot.set_position(unreal.Vector2D(*position)); item.slot.set_size(unreal.Vector2D(*size)); item.slot.set_alignment(unreal.Vector2D(*align))
    U.call_method('ToggleWidgetAsVariable', (bp,item.widget,True))
BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)
assert bp.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE
assert A.save_loaded_asset(bp, only_if_is_dirty=False)
(OUT/'T22_assets.json').write_text(json.dumps(dict(status='PASS', backup=str(backup), widgets=4),indent=2),encoding='utf-8')
unreal.log('[V03 T22] PASS')
