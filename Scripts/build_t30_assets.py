"""Rebuild Observer materials/config, opt-in pool and two-line threat HUD only."""
import json,shutil,hashlib
from pathlib import Path
from datetime import datetime
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'Saved/V04/T30'/('Assets_'+datetime.now().strftime('%Y%m%dT%H%M%S%f'));OUT.mkdir(parents=True)
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);T=unreal.AssetToolsHelpers.get_asset_tools();U=unreal.get_default_object(unreal.UMGToolSet)
names=['Body','Eye','RedEye']; base='/Game/Prototype/Observer'
mutable=['Content/Prototype/Maps/L_Prototype.umap','Content/UI/WBP_HealthThreat.uasset','Content/Prototype/Observer/DA_ObserverConfig.uasset']
mutable += ['Content/Prototype/Observer/M_Observer'+n+'.uasset' for n in names]
mutable += ['Content/Prototype/Data/Regions/DA_Region_'+r+'.uasset' for r in 'ABC']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'Content').rglob('*') if p.is_file() and p.relative_to(ROOT).as_posix() not in mutable}
for rel in mutable:
    p=ROOT/rel
    if p.exists():q=OUT/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
materials=[]
for name,rgb,glow in [('Body',(.42,.52,.55),0),('Eye',(.02,.8,1.),4),('RedEye',(1.,.008,.002),4)]:
    path=base+'/M_Observer'+name
    m=A.load_asset(path) if A.does_asset_exist(path) else T.create_asset('M_Observer'+name,base,unreal.Material,unreal.MaterialFactoryNew())
    unreal.MaterialEditingLibrary.delete_all_material_expressions(m)
    for prop,color in [(unreal.MaterialProperty.MP_BASE_COLOR,rgb),(unreal.MaterialProperty.MP_EMISSIVE_COLOR,tuple(v*glow for v in rgb))]:
        n=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionConstant3Vector)
        n.set_editor_property('constant',unreal.LinearColor(*color,1));unreal.MaterialEditingLibrary.connect_material_property(n,'',prop)
    unreal.MaterialEditingLibrary.recompile_material(m);assert A.save_loaded_asset(m,only_if_is_dirty=False);materials.append(m)
path=base+'/DA_ObserverConfig';cfg=A.load_asset(path) if A.does_asset_exist(path) else None
if not cfg:
    f=unreal.DataAssetFactory();f.set_editor_property('data_asset_class',unreal.AnomalyObserverConfig.static_class())
    cfg=T.create_asset('DA_ObserverConfig',base,unreal.AnomalyObserverConfig.static_class(),f)
values=dict(observe_distance=2000.,enter_dot=.8,exit_dot=.72,lost_sight_grace=.18,minimum_dwell=.2,acquire_seconds=.08,contact_grace=.35,observation_tolerance=4.,unobservable_seconds=1.25,mixed_pool_weight=.35)
for k,v in values.items():cfg.set_editor_property(k,v)
for k,v in zip(['body_material','eye_material','red_eye_material'],materials):cfg.set_editor_property(k,v)
assert A.save_loaded_asset(cfg,only_if_is_dirty=False)
for r in 'ABC':
    region=A.load_asset('/Game/Prototype/Data/Regions/DA_Region_'+r);region.set_editor_property('allowed_anomalies',['Chaser','Observer']);assert A.save_loaded_asset(region,only_if_is_dirty=False)
assert L.load_level('/Game/Prototype/Maps/L_Prototype')
c=next(x for x in E.get_all_level_actors() if isinstance(x,unreal.AnomalyRoundCoordinator))
c.set_editor_property('enable_observer_pool',True);c.set_editor_property('observer_class',unreal.AnomalyObserverCharacter.static_class());c.set_editor_property('observer_config',cfg)
assert L.save_current_level()
bp=A.load_asset('/Game/UI/WBP_HealthThreat');w={str(x.widget.get_name()):x.widget for x in U.call_method('GetWidgets',(bp,)).widgets if x.widget}
w['ThreatText'].slot.set_size(unreal.Vector2D(600,90));w['ThreatText'].set_font_size(22)
BlueprintTools.compile_blueprint(bp,warnings_as_errors=True);assert A.save_loaded_asset(bp,only_if_is_dirty=False)
unreal.AnomalyRoundCoordinator.finish_asset_compilation()
assert all(sha(ROOT/rel)==digest for rel,digest in protected.items()),'Unrelated Content changed'
(OUT/'report.json').write_text(json.dumps(dict(status='PASS',config=values,changed=mutable,protected_files=len(protected)),ensure_ascii=False,indent=2),encoding='utf-8')
