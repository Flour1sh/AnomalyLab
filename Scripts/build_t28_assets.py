"""Idempotent T28 config + minimal additions to existing Exploration HUD and map instance."""
import json,shutil
from datetime import datetime
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'Saved/V04/T28'/('Assets_'+datetime.now().strftime('%Y%m%dT%H%M%S%f'))
OUT.mkdir(parents=True)
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem); L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); U=unreal.get_default_object(unreal.UMGToolSet)
for rel in ['Content/Prototype/Maps/L_Prototype.umap','Content/UI/WBP_ExplorationPrompt.uasset','Content/Prototype/Data/DA_ProgressionConfig.uasset']:
    src=ROOT/rel
    if src.exists():
        dst=OUT/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
path='/Game/Prototype/Data/DA_ProgressionConfig'
cfg=A.load_asset(path) if A.does_asset_exist(path) else None
if not cfg:
    f=unreal.DataAssetFactory(); f.set_editor_property('data_asset_class',unreal.AnomalyProgressionConfig.static_class())
    cfg=unreal.AssetToolsHelpers.get_asset_tools().create_asset('DA_ProgressionConfig','/Game/Prototype/Data',unreal.AnomalyProgressionConfig.static_class(),f)
values=dict(prices=[1000,1500,2500,600],max_levels=[2,2,1,1],charges_per_level=1,precision_per_level=.25,precision_cap=.5,decoy_radius=1200.,decoy_seconds=5.,decoy_cooldown=3.)
for k,v in values.items(): cfg.set_editor_property(k,v)
assert A.save_loaded_asset(cfg,only_if_is_dirty=False)
assert L.load_level('/Game/Prototype/Maps/L_Prototype')
c=next(x for x in E.get_all_level_actors() if isinstance(x,unreal.AnomalyRoundCoordinator))
c.set_editor_property('use_preparation',True); c.set_editor_property('progression_config',cfg)
assert L.save_current_level()
bp=A.load_asset('/Game/UI/WBP_ExplorationPrompt')
w={str(x.widget.get_name()):x.widget for x in U.call_method('GetWidgets',(bp,)).widgets if x.widget}
root=w['ExplorationCanvas']
for name,cls,pos,size,font,z in [('ShopBacking',unreal.Image,(-700,-350),(1400,700),0,30),('ShopText',unreal.TextBlock,(-660,-320),(1320,650),24,31),('MetaText',unreal.TextBlock,(380,-460),(550,45),18,20)]:
    item=w.get(name) or U.call_method('AddWidget',(bp,cls.static_class(),name,root,-1)).widget
    slot=item.slot; slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(.5,.5),maximum=unreal.Vector2D(.5,.5)))
    slot.set_position(unreal.Vector2D(*pos)); slot.set_size(unreal.Vector2D(*size)); slot.set_z_order(z)
    if font:
        item.set_font_size(font); item.set_text(unreal.Text('')); item.set_auto_wrap_text(True)
        item.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(.82,.97,.92,1)))
        item.set_shadow_offset(unreal.Vector2D(1,1)); item.set_shadow_color_and_opacity(unreal.LinearColor(0,0,0,1))
    else: item.set_color_and_opacity(unreal.LinearColor(.012,.025,.028,.96))
    U.call_method('ToggleWidgetAsVariable',(bp,item,True))
BlueprintTools.compile_blueprint(bp,warnings_as_errors=True); assert A.save_loaded_asset(bp,only_if_is_dirty=False)
(OUT/'report.json').write_text(json.dumps(dict(status='PASS',config=values),indent=2),encoding='utf-8')
