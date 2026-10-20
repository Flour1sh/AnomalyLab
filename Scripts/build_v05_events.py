"""T40 seeds/config and alarm lights; duplicates only the Lab's passive HUD."""
import json,hashlib
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[1]
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);U=unreal.get_default_object(unreal.UMGToolSet)
old=[r for r in json.loads((ROOT/'Saved/V05/T33/source_copy_manifest.json').read_text(encoding='utf-8'))['files'] if r['path'].startswith('Content/')]
assert all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in old)
assert L.load_level('/Game/Maps/L_Lab');config=A.load_asset('/Game/Prototype/V05/Data/DA_Environment');assert config
config.set_editor_property('enable_events',True)
for key,value in dict(EventChance=.5,MaxEvents=2,EventFirstDelay=12,EventSpacing=10,EventWarningSeconds=2,EventSeconds=4,AlarmSpeedMultiplier=1.08).items():config.set_editor_property(key,value)
assert A.save_loaded_asset(config,only_if_is_dirty=False)
lights=[]
for actor in E.get_all_level_actors():
    p=actor.get_actor_location()
    if isinstance(actor,unreal.PointLight) and -800<p.x<800 and -1500<p.y<-500:
        tags=list(actor.get_editor_property('tags'))
        if 'V05AlarmC' not in [str(t) for t in tags]:tags.append('V05AlarmC');actor.set_editor_property('tags',tags)
        actor.point_light_component.set_mobility(unreal.ComponentMobility.MOVABLE);lights.append(actor.get_actor_label())
assert lights
target='/Game/Prototype/V05/UI/WBP_LabPrompt';hud=A.load_asset(target) if A.does_asset_exist(target) else A.duplicate_asset('/Game/UI/WBP_ExplorationPrompt',target);assert hud
widgets={str(x.widget.get_name()):x.widget for x in U.call_method('GetWidgets',(hud,)).widgets if x.widget}
# Keep original named native bindings; enlarge only the objective area in this copy.
names=list(widgets)
original=A.load_asset('/Game/UI/WBP_ExplorationPrompt')
base={str(x.widget.get_name()):x.widget for x in U.call_method('GetWidgets',(original,)).widgets if x.widget}
for name,item in widgets.items():
    if name=='ExplorationObjective' and isinstance(item.slot,unreal.CanvasPanelSlot):
        size=base[name].slot.get_size();item.slot.set_size(unreal.Vector2D(size.x,240))
    if name=='InventoryText' and isinstance(item.slot,unreal.CanvasPanelSlot):
        position=base[name].slot.get_position();item.slot.set_position(unreal.Vector2D(position.x,position.y+140))
from editor_toolset.toolsets.blueprint import BlueprintTools
BlueprintTools.compile_blueprint(hud,warnings_as_errors=True);assert A.save_loaded_asset(hud,only_if_is_dirty=False)
owners=[x for x in E.get_all_level_actors() if isinstance(x,unreal.AnomalyRoundCoordinator)];assert len(owners)==1
owners[0].set_editor_property('ExplorationWidgetClass',A.load_blueprint_class(target));assert L.save_current_level()
assert all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in old)
out=ROOT/'Saved/V05/T40';out.mkdir(parents=True,exist_ok=True);(out/'events_build.json').write_text(json.dumps(dict(status='PASS',lights=lights,actors=len(E.get_all_level_actors()),max_events=2,warning_seconds=2,duration=4,spacing=10,quiet_probability=.5,hud_widgets=names,protected_content=len(old)),indent=2),encoding='utf-8')
unreal.log('[T40 BUILD] PASS')
