import unreal, json
from pathlib import Path
from editor_toolset.toolsets.actor import ActorTools
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert L.load_level('/Game/Prototype/Maps/L_Prototype')
result={}
for actor in E.get_all_level_actors():
    label=actor.get_actor_label()
    if label in ('T20_Entry_Floor','T20_Wall_00','T20_ReturnLine'):
        mat=actor.static_mesh_component.get_material(0)
        result[label]=dict(material=mat.get_path_name(),class_name=mat.get_class().get_name(),expressions=unreal.MaterialEditingLibrary.get_num_material_expressions(mat))
    if isinstance(actor,unreal.RecastNavMesh):
        result['nav']=dict(radius=actor.get_editor_property('agent_radius'),height=actor.get_editor_property('agent_height'))
bp=A.load_asset('/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter')
components=ActorTools.get_components(unreal.get_default_object(bp.generated_class()))
result['capsule']=[dict(radius=c.get_unscaled_capsule_radius(),height=c.get_unscaled_capsule_half_height()) for c in components if isinstance(c,unreal.CapsuleComponent)]
Path(unreal.Paths.project_saved_dir(),'V03/render_inspection.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
