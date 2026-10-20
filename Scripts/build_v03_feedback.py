"""T24 deterministic locally synthesized sound assets and non-flashing HUD feedback."""
from pathlib import Path
from datetime import datetime
import json, math, struct, wave, shutil
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'Saved/V03'
A = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
L = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
U = unreal.get_default_object(unreal.UMGToolSet)
backup = OUT/('T24AssetsBefore_' + datetime.now().strftime('%Y%m%dT%H%M%S%f'))
for path in [ROOT/'Content/UI/WBP_ExplorationPrompt.uasset', ROOT/'Content/UI/Menu/WBP_MainMenu.uasset', ROOT/'Content/Prototype/Maps/L_Prototype.umap',
             *list((ROOT/'Content/Prototype/Audio').glob('*.uasset'))]:
    if path.exists():
        target = backup/path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path,target)
source = ROOT/'GameAudio'
source.mkdir(exist_ok=True)
sounds = {}
for event, frequency, duration in [('ScanStart',660,1.1),('ScanComplete',1100,.2),('Pickup',900,.18),('Reveal',460,.3),
                                   ('Warning',180,1.),('Threat',75,2.),('Damage',95,.18),('Extract',720,.7),('Containment',540,.45)]:
    rate = 24000
    samples = bytearray()
    for index in range(int(rate*duration)):
        t = index/rate
        envelope = min(1., t/.008) * min(1., (duration-t)/.04)
        if event == 'ScanStart': envelope *= .15 if int(t*10)%2 else 1.
        pitch = frequency * (1 + .35*t/duration if event in ('Extract','ScanComplete','Pickup') else 1)
        value = .17 * envelope * (math.sin(2*math.pi*pitch*t) + .25*math.sin(2*math.pi*pitch*1.5*t))
        samples.extend(struct.pack('<h', int(value*32767)))
    path = source/('S_'+event+'.wav')
    with wave.open(str(path),'wb') as stream:
        stream.setparams((1,2,rate,len(samples)//2,'NONE','not compressed')); stream.writeframes(samples)
    task = unreal.AssetImportTask()
    for key,value in dict(filename=str(path),destination_path='/Game/Prototype/Audio',automated=True,replace_existing=True,save=True).items():
        task.set_editor_property(key,value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sound = A.load_asset('/Game/Prototype/Audio/S_'+event)
    assert sound
    sound.set_editor_property('looping', event == 'Threat')
    assert A.save_loaded_asset(sound,only_if_is_dirty=False)
    sounds[event] = sound
assert L.load_level('/Game/Prototype/Maps/L_Prototype')
coordinator = next(a for a in E.get_all_level_actors() if isinstance(a,unreal.AnomalyRoundCoordinator))
coordinator.set_editor_property('feedback_sounds', sounds)
assert L.save_current_level()
bp = A.load_asset('/Game/UI/WBP_ExplorationPrompt')
widgets = U.call_method('GetWidgets',(bp,)).widgets
by_name = {str(w.widget.get_name()):w.widget for w in widgets if w.widget}
root = by_name['ExplorationCanvas']
if 'DamageVeil' not in by_name:
    item = U.call_method('AddWidget',(bp,unreal.Image.static_class(),'DamageVeil',root,-1))
    item.widget.set_color_and_opacity(unreal.LinearColor(.55,.015,.005,1))
    item.widget.set_render_opacity(0.)
    item.slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(0,0),maximum=unreal.Vector2D(1,1)))
    item.slot.set_offsets(unreal.Margin(0,0,0,0)); item.slot.set_z_order(-10)
    U.call_method('ToggleWidgetAsVariable',(bp,item.widget,True))
if 'Crosshair' not in by_name:
    item = U.call_method('AddWidget',(bp,unreal.TextBlock.static_class(),'Crosshair',root,-1))
    item.widget.set_text(unreal.Text('+')); item.widget.set_font_size(20)
    item.widget.set_editor_property('justification',unreal.TextJustify.CENTER)
    item.slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(.5,.5),maximum=unreal.Vector2D(.5,.5)))
    item.slot.set_alignment(unreal.Vector2D(.5,.5)); item.slot.set_position(unreal.Vector2D(0,0)); item.slot.set_size(unreal.Vector2D(24,30))
BlueprintTools.compile_blueprint(bp,warnings_as_errors=True)
assert bp.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE
assert A.save_loaded_asset(bp,only_if_is_dirty=False)
menu = A.load_asset('/Game/UI/Menu/WBP_MainMenu')
widgets = {str(w.widget.get_name()):w.widget for w in U.call_method('GetWidgets',(menu,)).widgets if w.widget}
for name,text in {'GuideAction2':'打开箱子 / 拾取物品 / 入口确认撤离',
                  'GuideAction4':'决策时继续 / 选择返回入口',
                  'GuideRule':'四格背包；仅入口按 E 撤离后兑现。死亡丢失携带物品。'}.items():
    assert name in widgets,name
    widgets[name].set_text(unreal.Text(text))
BlueprintTools.compile_blueprint(menu,warnings_as_errors=True)
assert menu.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE
assert A.save_loaded_asset(menu,only_if_is_dirty=False)
(OUT/'T24_assets.json').write_text(json.dumps(dict(status='PASS',sounds=list(sounds),backup=str(backup),flashing='none'),indent=2),encoding='utf-8')
unreal.log('[V03 T24] PASS')


