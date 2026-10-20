"""Read the current level for menu staging; never save it."""
import json
from pathlib import Path
import unreal

root = Path(__file__).resolve().parent.parent
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert level.load_level('/Game/Prototype/Maps/L_Prototype')
records = []
for actor in actors.get_all_level_actors():
    location = actor.get_actor_location()
    entry = dict(name=actor.get_name(), label=actor.get_actor_label(),
                 cls=actor.get_class().get_path_name(), location=[location.x, location.y, location.z])
    if isinstance(actor, unreal.StaticMeshActor):
        mesh = actor.static_mesh_component.static_mesh
        entry['mesh'] = mesh.get_path_name() if mesh else None
    records.append(entry)
out = root / 'Saved/T19Menu'
out.mkdir(parents=True, exist_ok=True)
(out / 'baseline_actors.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('[T19Menu] INSPECTION PASS')
