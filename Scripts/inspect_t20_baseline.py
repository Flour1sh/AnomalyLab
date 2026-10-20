"""Read the saved T20 starting map and interaction graphs, without gameplay or saves."""
import json
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Saved/T20'
OUT.mkdir(parents=True, exist_ok=True)
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert level.load_level('/Game/Prototype/Maps/L_Prototype')
report = {'actors': [], 'graphs': {}, 'python_api': {}}
for actor in actors.get_all_level_actors():
    entry = dict(label=actor.get_actor_label(), cls=actor.get_class().get_path_name(),
                 location=str(actor.get_actor_location()), rotation=str(actor.get_actor_rotation()),
                 scale=str(actor.get_actor_scale3d()))
    if isinstance(actor, unreal.StaticMeshActor):
        mesh = actor.static_mesh_component.static_mesh
        entry['mesh'] = mesh.get_path_name() if mesh else None
        entry['bounds'] = str(actor.get_actor_bounds(False))
    if isinstance(actor, unreal.AnomalyRoundCoordinator):
        entry['points'] = {p: str(actor.get_editor_property(p).get_editor_property('relative_location'))
                           for p in ('box_point_left', 'box_point_middle', 'box_point_right')}
    report['actors'].append(entry)
bp = assets.load_asset('/Game/Core/Components/BPC_Interaction')
for graph in BlueprintTools.list_graphs(bp):
    nodes = []
    for node in BlueprintTools.find_nodes(graph):
        pins = list(unreal.BlueprintEditorLibrary.list_input_pins(node))
        nodes.append(dict(name=node.get_name(), title=str(node.get_node_title()),
                          pins={str(p.get_pin_name()): str(p.get_pin_value()) for p in pins}))
    report['graphs'][graph.get_name()] = nodes
for cls in (unreal.LevelEditorSubsystem, unreal.EditorLevelLibrary, unreal.NavigationSystemV1,
            unreal.BlueprintEditorLibrary):
    report['python_api'][cls.__name__] = [s for s in dir(cls) if any(x in s.lower() for x in ('build', 'navigation', 'compile'))]
(OUT / 'baseline_inspection.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('[T20] BASELINE READ COMPLETE')
