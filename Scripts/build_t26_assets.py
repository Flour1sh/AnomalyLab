"""Idempotent T26 authoring: three region assets, two HUD children, map-instance references only."""
import json, hashlib, shutil, sys
from datetime import datetime
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
from t26_data import REGIONS
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
U=unreal.get_default_object(unreal.UMGToolSet)
OUT=ROOT/'Saved/V04/T26'; OUT.mkdir(parents=True,exist_ok=True)
mutable=['Content/Prototype/Maps/L_Prototype.umap','Content/UI/WBP_ExplorationPrompt.uasset']
mutable += ['Content/Prototype/Data/Regions/DA_Region_'+r['region_id']+'.uasset' for r in REGIONS]
backup=OUT/('AssetsBefore_'+datetime.now().strftime('%Y%m%dT%H%M%S%f'))
for name in mutable:
    source=ROOT/name
    if source.exists():
        target=backup/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target)
digest=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
protected={p.relative_to(ROOT).as_posix():digest(p) for p in (ROOT/'Content').rglob('*')
           if p.is_file() and p.relative_to(ROOT).as_posix() not in mutable}
assets=[]
for row in REGIONS:
    name='DA_Region_'+row['region_id']; path='/Game/Prototype/Data/Regions/'+name
    asset=A.load_asset(path) if A.does_asset_exist(path) else None
    if not asset:
        factory=unreal.DataAssetFactory(); factory.set_editor_property('data_asset_class',unreal.AnomalyRegionDefinition.static_class())
        asset=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,'/Game/Prototype/Data/Regions',unreal.AnomalyRegionDefinition.static_class(),factory)
    assert asset
    for key,value in row.items():
        asset.set_editor_property(key,unreal.Text(value) if key in ('display_name','description') else value)
    asset.set_editor_property('allowed_anomalies',['Chaser'])
    assert A.save_loaded_asset(asset,only_if_is_dirty=False)
    assets.append(asset)
assert L.load_level('/Game/Prototype/Maps/L_Prototype')
c=next(a for a in E.get_all_level_actors() if isinstance(a,unreal.AnomalyRoundCoordinator))
c.set_editor_property('use_region_rules',True)
c.set_editor_property('region_rules',assets)
c.set_editor_property('use_fixed_region_seed',False)
assert L.save_current_level()
bp=A.load_asset('/Game/UI/WBP_ExplorationPrompt')
widgets={str(w.widget.get_name()):w.widget for w in U.call_method('GetWidgets',(bp,)).widgets if w.widget}
root=widgets['ExplorationCanvas']
for name,cls in [('RegionBacking',unreal.Image),('RegionText',unreal.TextBlock)]:
    widget=widgets.get(name)
    if not widget:
        widget=U.call_method('AddWidget',(bp,cls.static_class(),name,root,-1)).widget
    slot=widget.slot
    slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(0,0),maximum=unreal.Vector2D(0,0)))
    slot.set_alignment(unreal.Vector2D(0,0))
    if name=='RegionBacking':
        widget.set_color_and_opacity(unreal.LinearColor(.008,.02,.015,.84))
        slot.set_position(unreal.Vector2D(16,162)); slot.set_size(unreal.Vector2D(660,126)); slot.set_z_order(-1)
    else:
        widget.set_text(unreal.Text(''))
        widget.set_font_size(20)
        widget.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(.78,.95,.87,1)))
        widget.set_shadow_offset(unreal.Vector2D(1,1)); widget.set_shadow_color_and_opacity(unreal.LinearColor(0,0,0,1))
        slot.set_position(unreal.Vector2D(24,170)); slot.set_size(unreal.Vector2D(644,112))
        U.call_method('ToggleWidgetAsVariable',(bp,widget,True))
BlueprintTools.compile_blueprint(bp,warnings_as_errors=True)
assert bp.get_editor_property('status')==unreal.BlueprintStatus.BS_UP_TO_DATE
assert A.save_loaded_asset(bp,only_if_is_dirty=False)
assert all(digest(ROOT/p)==sha for p,sha in protected.items()),'Unrelated assets changed'
(OUT/'assets.json').write_text(json.dumps(dict(status='PASS',backup=str(backup),mutable=mutable,
    protected_sha256=protected,protected_count=len(protected),regions=[a.get_path_name() for a in assets]),ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[T26 ASSETS] PASS')
