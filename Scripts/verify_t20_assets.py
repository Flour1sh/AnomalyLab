"""Reload saved T20 packages in a separate editor process. Never starts gameplay."""
import hashlib
import json
import sys
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'Scripts'))
from t20_layout import MAP, LEGACY, UI, ENV, BOX_POINTS, ENTRANCE, START, THREAT_OFFSET, ROOMS, WALLS
OUT = ROOT / 'Saved/T20'
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVEL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
checks = []


def check(name, value):
    checks.append(dict(check=name, passed=bool(value)))
    assert value, name


def xyz(value):
    return (round(value.x, 3), round(value.y, 3), round(value.z, 3))


report = json.loads((OUT / 'build_report.json').read_text(encoding='utf-8'))
for path in ASSETS.list_assets(ENV, recursive=True, include_folder=False):
    check('Reload ' + str(path), ASSETS.load_asset(path) is not None)
widget = ASSETS.load_asset(UI)
check('Widget parent', isinstance(unreal.get_default_object(widget.generated_class()), unreal.AnomalyExplorationWidget))
BlueprintTools.compile_blueprint(widget, warnings_as_errors=True)
check('Widget compiles without warnings', widget.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE)
widgets = unreal.get_default_object(unreal.UMGToolSet).call_method('GetWidgets', (widget,)).widgets
names = [w.widget.get_name() for w in widgets]
check('Unique widget tree', len(names) == len(set(names)) == 3)
check('Native text bindings', {'InteractionPrompt', 'ExplorationObjective'} <= set(names))
player = ASSETS.load_asset('/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter')
BlueprintTools.compile_blueprint(player, warnings_as_errors=True)
check('Player compiles without warnings', player.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE)
graph = unreal.BlueprintEditorLibrary.find_graph(player, 'T06Restart')
types = [BlueprintTools._get_node_info(n).type_id for n in BlueprintTools.find_nodes(graph)]
check('One current-map restart source', sum('GetCurrentLevelName' in t for t in types) == 1)
restart_nodes = BlueprintTools.find_nodes(graph)
get_level = next(n for n in restart_nodes if 'GetCurrentLevelName' in BlueprintTools._get_node_info(n).type_id)
get_exec = next(p for p in unreal.BlueprintEditorLibrary.list_input_pins(get_level) if str(p.get_pin_name()) == 'execute')
check('Current-map lookup execution connected', len(get_exec.list_connected_pins()) == 1)
check('Saved generation report contains actual nav tiles', report['navigation_valid_tiles'] > 0)

check('Load exploration map', LEVEL.load_level(MAP))
actors = list(ACTORS.get_all_level_actors())
generated = [a for a in actors if a.get_actor_label().startswith('T20_')]
labels = [a.get_actor_label() for a in generated]
check('Generated actor count matches save', len(generated) == report['generated_actors'])
check('No duplicate generated labels', len(labels) == len(set(labels)))
check('Five floor modules', sum(label.endswith('_Floor') for label in labels) == len(ROOMS))
check('Authored walls persisted', sum(label.startswith('T20_Wall_') for label in labels) == len(WALLS))
spawners = [a for a in actors if isinstance(a, unreal.AnomalyRoundCoordinator)]
check('One authoritative coordinator', len(spawners) == 1)
coordinator = spawners[0]
check('Exploration is map instance mode', coordinator.get_editor_property('play_mode') == unreal.AnomalyPlayMode.EXPLORATION)
check('Widget saved on map instance', coordinator.get_editor_property('exploration_widget_class') == widget.generated_class())
check('Range 300 cm', coordinator.get_editor_property('interaction_range') == 300.)
check('Entrance position saved', xyz(coordinator.get_editor_property('entrance_location')) == ENTRANCE)
check('Monster spawn offset saved', xyz(coordinator.get_editor_property('exploration_threat_offset')) == THREAT_OFFSET)
for name, point in zip(('box_point_left', 'box_point_middle', 'box_point_right'), BOX_POINTS):
    check(name + ' separated position', xyz(coordinator.get_editor_property(name).get_editor_property('relative_location')) == point)
check('No placed gameplay boxes', not any(isinstance(a, unreal.AnomalyBoxActor) for a in actors))
starts = [a for a in actors if isinstance(a, unreal.PlayerStart)]
check('One PlayerStart at entrance', len(starts) == 1 and xyz(starts[0].get_actor_location()) == START)
check('PlayerStart faces hallway', abs(starts[0].get_actor_rotation().yaw + 90.) < .001 and abs(starts[0].get_actor_rotation().pitch) < .001)
bounds = [a for a in actors if isinstance(a, unreal.NavMeshBoundsVolume)]
check('Navigation volume covers authored footprint', len(bounds) == 1 and xyz(bounds[0].get_actor_scale3d()) == (15, 19, 4))
navs = [a for a in actors if isinstance(a, unreal.RecastNavMesh)]
check('Recast uses dynamic runtime generation', len(navs) == 1 and navs[0].get_editor_property('runtime_generation') == unreal.RuntimeGenerationType.DYNAMIC)
for obj in generated:
    if obj.get_actor_label().startswith('T20_Wall_') or obj.get_actor_label().endswith('_Floor'):
        check(obj.get_actor_label() + ' blocking collision', obj.static_mesh_component.get_collision_profile_name() == 'BlockAll')
check('Load legacy map', LEVEL.load_level(LEGACY))
legacy = [a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.AnomalyRoundCoordinator)]
check('Legacy mode retained', len(legacy) == 1 and legacy[0].get_editor_property('play_mode') == unreal.AnomalyPlayMode.LEGACY_PROTOTYPE)
for name, point in zip(('box_point_left', 'box_point_middle', 'box_point_right'), ((0, -220, 0), (0, 0, 0), (0, 220, 0))):
    check('Legacy ' + name, xyz(legacy[0].get_editor_property(name).get_editor_property('relative_location')) == point)
check('Legacy disk asset unchanged by reload', hashlib.sha256((ROOT / 'Content/Prototype/Maps/L_LegacyPrototype.umap').read_bytes()).hexdigest() == report['legacy_sha256'])
for path, sha in report['protected_sha256'].items():
    check('Protected ' + path, hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha)
result = dict(status='PASS', scope='Saved asset reload/compile only', checks=checks,
              gameplay_tested=False, visual='NOT RUN', manual='PENDING_MANUAL',
              navigation_paths='NOT RUN', generated_actors=len(generated))
(OUT / 'reload_report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('[T20] RELOAD PASS')
