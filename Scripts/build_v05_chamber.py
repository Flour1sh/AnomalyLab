"""T39 chamber console and visible volume, only L_Lab/V05 data."""
import json,hashlib
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[1]
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
old=[r for r in json.loads((ROOT/'Saved/V05/T33/source_copy_manifest.json').read_text(encoding='utf-8'))['files'] if r['path'].startswith('Content/')]
assert all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in old)
assert L.load_level('/Game/Maps/L_Lab')
config=A.load_asset('/Game/Prototype/V05/Data/DA_Environment');assert config
config.set_editor_property('enable_chamber',True);config.set_editor_property('ChamberCenter',unreal.Vector(300,-1100,0));config.set_editor_property('ChamberRadius',300);config.set_editor_property('ChamberSeconds',3)
assert A.save_loaded_asset(config,only_if_is_dirty=False)
for obj in list(E.get_all_level_actors()):
    if obj.get_actor_label().startswith('T39Owned_'):assert E.destroy_actor(obj)
def spawn(cls,name,xyz,yaw=0):
    obj=E.spawn_actor_from_class(cls,unreal.Vector(*xyz),unreal.Rotator(pitch=0,yaw=yaw,roll=0),transient=False);assert obj
    obj.set_actor_label('T39Owned_'+name);return obj
console=spawn(unreal.AnomalyEnvironmentTerminal,'C_Chamber',(700,-1120,95),-90);console.set_editor_property('Kind',unreal.AnomalyEnvironmentKind.CHAMBER)
visual=console.get_editor_property('Visual');visual.set_static_mesh(A.load_asset('/Game/Prototype/Environment/ScenePolish/SM_SP_ReturnTerminal'));visual.set_relative_location(unreal.Vector(0,0,-95),False,False)
pad=spawn(unreal.StaticMeshActor,'ChamberVolume',(300,-1100,1));pad.static_mesh_component.set_static_mesh(A.load_asset('/Engine/BasicShapes/Cylinder'));pad.set_actor_scale3d(unreal.Vector(6,6,.015));pad.static_mesh_component.set_collision_profile_name('NoCollision');pad.static_mesh_component.set_material(0,A.load_asset('/Game/Prototype/V05/Environment/M_HubMint'))
sign=spawn(unreal.TextRenderActor,'C_Sign',(785,-1120,285),180);sign.text_render.set_text(unreal.Text('C STASIS  /  E'));sign.text_render.set_world_size(30);sign.text_render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER);sign.text_render.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();tiles=unreal.AnomalyRoundCoordinator.build_exploration_navigation(world);assert tiles>0
assert L.save_current_level();assert all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in old)
out=ROOT/'Saved/V05/T39';out.mkdir(parents=True,exist_ok=True);(out/'chamber_build.json').write_text(json.dumps(dict(status='PASS',actors=len(E.get_all_level_actors()),radius=300,seconds=3,nav_tiles=tiles,protected_content=len(old)),indent=2),encoding='utf-8')
unreal.log('[T39 BUILD] PASS')
