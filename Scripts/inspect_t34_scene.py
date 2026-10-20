"""Read existing scene/pawn defaults needed for T34; no asset saves."""
import json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'Saved/V05/T34';OUT.mkdir(parents=True,exist_ok=True)
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem); L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert L.load_level('/Game/Prototype/Maps/L_Prototype')
player=E.spawn_actor_from_class(A.load_asset('/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter').generated_class(),unreal.Vector(0,1750,110),unreal.Rotator(),transient=True)
movement=player.get_component_by_class(unreal.CharacterMovementComponent); camera=player.get_component_by_class(unreal.CameraComponent); capsule=player.get_component_by_class(unreal.CapsuleComponent)
report=dict(movement={k:movement.get_editor_property(k) for k in ['max_walk_speed','jump_z_velocity','gravity_scale','air_control','max_acceleration','braking_deceleration_walking']},camera=dict(location=list(camera.get_editor_property('relative_location').to_tuple()),fov=camera.get_editor_property('field_of_view')),capsule=dict(radius=capsule.get_unscaled_capsule_radius(),half_height=capsule.get_unscaled_capsule_half_height()),assets={})
assert E.destroy_actor(player)
for folder in ['/Game/Prototype/Environment/ScenePolish','/Game/Prototype/Environment/T20','/Game/LowPolyLabPrototype','/Game/UI/Menu']:
    report['assets'][folder]=[str(p) for p in A.list_assets(folder,recursive=True,include_folder=False)]
assert L.load_level('/Game/Prototype/Maps/L_Prototype')
report['scene']=[dict(label=x.get_actor_label(),cls=x.get_class().get_path_name(),location=list(x.get_actor_location().to_tuple()),mesh=x.static_mesh_component.static_mesh.get_path_name() if isinstance(x,unreal.StaticMeshActor) and x.static_mesh_component.static_mesh else None) for x in E.get_all_level_actors()]
(OUT/'scene_inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[T34 INSPECT] PASS')
