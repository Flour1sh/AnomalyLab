"""T38 owns service/terminal/sign in L_Lab; light tags belong to this copy only."""
import json,hashlib
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[1]
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
manifest=json.loads((ROOT/'Saved/V05/T33/source_copy_manifest.json').read_text(encoding='utf-8'))
old=[r for r in manifest['files'] if r['path'].startswith('Content/')]
def protect():assert all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in old)
protect(); assert L.load_level('/Game/Maps/L_Lab')
path='/Game/Prototype/V05/Data/DA_Environment';config=A.load_asset(path)
if not config:
    factory=unreal.DataAssetFactory();factory.set_editor_property('data_asset_class',unreal.AnomalyEnvironmentConfig)
    config=unreal.AssetToolsHelpers.get_asset_tools().create_asset('DA_Environment','/Game/Prototype/V05/Data',unreal.AnomalyEnvironmentConfig,factory)
assert config
for name,value in dict(PowerScanMultiplier=1.75,PowerObserveMultiplier=1.5,PowerLightMultiplier=.25,InteractCooldown=.35).items():config.set_editor_property(name,value)
assert A.save_loaded_asset(config,only_if_is_dirty=False)
for actor in list(E.get_all_level_actors()):
    if actor.get_actor_label().startswith('T38Owned_'):assert E.destroy_actor(actor)
def spawn(cls,name,xyz,yaw=0):
    actor=E.spawn_actor_from_class(cls,unreal.Vector(*xyz),unreal.Rotator(pitch=0,yaw=yaw,roll=0),transient=False);assert actor
    actor.set_actor_label('T38Owned_'+name);return actor
service=spawn(unreal.AnomalyEnvironmentController,'EnvironmentService',(0,0,0));service.set_editor_property('Config',config)
power=spawn(unreal.AnomalyEnvironmentTerminal,'B_Power',(650,780,95),90)
visual=power.get_editor_property('Visual');visual.set_static_mesh(A.load_asset('/Game/Prototype/Environment/ScenePolish/SM_SP_ReturnTerminal'));visual.set_relative_location(unreal.Vector(0,0,-95),False,False)
sign=spawn(unreal.TextRenderActor,'B_Sign',(650,860,280),90);sign.text_render.set_text(unreal.Text('B POWER  /  E'));sign.text_render.set_world_size(32);sign.text_render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER);sign.text_render.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
lights=[]
for actor in E.get_all_level_actors():
    xyz=actor.get_actor_location()
    if isinstance(actor,unreal.PointLight) and 240<xyz.x<1400 and -500<xyz.y<900:
        tags=list(actor.get_editor_property('tags'))
        if 'V05PowerB' not in [str(x) for x in tags]:tags.append('V05PowerB');actor.set_editor_property('tags',tags)
        actor.point_light_component.set_mobility(unreal.ComponentMobility.MOVABLE);lights.append(actor.get_actor_label())
assert lights
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
tiles=unreal.AnomalyRoundCoordinator.build_exploration_navigation(world);assert tiles>0
assert L.save_current_level();protect()
out=ROOT/'Saved/V05/T38';out.mkdir(parents=True,exist_ok=True)
(out/'power_build.json').write_text(json.dumps(dict(status='PASS',actors=len(E.get_all_level_actors()),service=service.get_actor_label(),power=power.get_actor_label(),lights=lights,nav_tiles=tiles,protected_content=len(old)),indent=2),encoding='utf-8')
unreal.log('[T38 BUILD] PASS')
