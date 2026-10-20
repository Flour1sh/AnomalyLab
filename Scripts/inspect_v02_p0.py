"""P0 Unreal load/compile/defaults/dependency inspection; never saves assets or runs PIE."""
import json
import sys
import traceback
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as B
from editor_toolset.toolsets.actor import ActorTools as A

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'Scripts'))
from prepare_t07 import PACKAGES

OUT = Path(json.loads((ROOT / 'Saved/P0/latest.json').read_text(encoding='utf-8'))['directory'])
REPORT = dict(scope='In-memory load/compile and saved defaults, no asset saves',
              status='RUNNING', assets={}, checks=[], errors=[], PIE='NOT RUN',
              visual_validation='NOT RUN', packaging='NOT RUN')
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)


def save_report():
    (OUT / 'unreal_inspection.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def check(label, condition, actual=None):
    REPORT['checks'].append(dict(check=label, passed=bool(condition), actual=actual))


def simple(value):
    if isinstance(value, (str, bool, int, float)) or value is None:
        return value
    if isinstance(value, unreal.Object):
        return value.get_path_name()
    return str(value)


def graph_data(bp):
    result = {}
    for graph in B.list_graphs(bp):
        nodes = []
        for node in B.find_nodes(graph):
            pins = []
            for direction, source in [('in', unreal.BlueprintEditorLibrary.list_input_pins(node)),
                                      ('out', unreal.BlueprintEditorLibrary.list_output_pins(node))]:
                for pin in source:
                    pins.append(dict(direction=direction, name=str(pin.get_pin_name()),
                                     value=str(pin.get_pin_value()),
                                     links=[p.get_owning_node().get_name()+'.'+str(p.get_pin_name())
                                            for p in pin.list_connected_pins()]))
            nodes.append(dict(name=node.get_name(), title=str(node.get_node_title()),
                              type=str(B._get_node_info(node).type_id), pins=pins))
        result[graph.get_name()] = nodes
    return result


def main():
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.wait_for_completion()
    missing_dependencies = []
    loaded = {}
    options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,
                                                    include_soft_package_references=True)
    for rel in PACKAGES:
        path = '/Game/' + rel
        if path.endswith('/L_Prototype'):
            continue
        asset = ASSETS.load_asset(path)
        check('Load ' + path, asset is not None)
        if not asset:
            continue
        loaded[path] = asset
        entry = REPORT['assets'][path] = dict(type=asset.get_class().get_name())
        if isinstance(asset, unreal.Blueprint):
            try:
                B.compile_blueprint(asset, warnings_as_errors=True)
                entry['compile'] = 'PASS'
            except Exception as exc:
                entry['compile'] = 'FAIL'
                REPORT['errors'].append(path + ': ' + str(exc))
            check('Compile ' + path, entry['compile'] == 'PASS')
            if asset.generated_class():
                cdo = unreal.get_default_object(asset.generated_class())
                defaults = {}
                for name in B.list_variables(asset):
                    try:
                        defaults[str(name)] = simple(cdo.get_editor_property(str(name)))
                    except Exception as exc:
                        defaults[str(name)] = {'inspection_error': str(exc)}
                entry['defaults'] = defaults
                entry['dispatchers'] = [str(x) for x in unreal.BlueprintEditorLibrary.list_event_dispatchers(asset)]
                entry['graphs'] = graph_data(asset)
            check('No graph errors ' + path, all(not unreal.BlueprintGraphEditor.get_graph_editor(g).list_nodes_with_errors()
                                                  for g in B.list_graphs(asset)))
        deps = [str(v) for v in registry.get_dependencies(path, options)]
        entry['game_dependencies'] = [d for d in deps if d.startswith('/Game/')]
        for dep in entry['game_dependencies']:
            if not ASSETS.does_asset_exist(dep):
                missing_dependencies.append(dict(asset=path, dependency=dep))
        unreal.log('[P0] Inspected ' + path)
        save_report()
    expected = {
        '/Game/Core/Components/BPC_Wallet': {'Money': 0},
        '/Game/Anomalies/Containers/BP_AnomalyBox': {'RevealDelay': 1.0, 'bOpened': False, 'bResolved': False, 'bForceOutcome': False},
        '/Game/Anomalies/Containers/BP_BoxSpawner': {'ThreatsResolved': 0, 'MaxThreats': 2, 'NextRoundDelay': 3.0, 'SpawnRetryDelay': 1.0, 'MaxSpawnRetries': 3},
        '/Game/Anomalies/Creatures/BP_Spider': {'MoveSpeed': 350.0, 'AcceptanceRadius': 80.0, 'AutoResolveDelay': 3.0, 'bAutoResolveThreat': True,
                                             'T10TurnSpeed': 8.0, 'T10StrideLength': 115.0, 'T10MotionScale': 1.0}}
    for path, values in expected.items():
        cdo = unreal.get_default_object(loaded[path].generated_class())
        for key, expected_value in values.items():
            actual = cdo.get_editor_property(key)
            check(path + '.' + key, actual == expected_value, simple(actual))
    spider = loaded['/Game/Anomalies/Creatures/BP_Spider']
    spider_cdo = unreal.get_default_object(spider.generated_class())
    check('Spider saved T10 build marker', ASSETS.get_metadata_tag(spider, 'T10BuildVersion') == '1')
    for name in ('T10FacePlayer', 'T10AnimateBody'):
        check('Spider graph ' + name, name in REPORT['assets'][spider.get_path_name().split('.')[0]]['graphs'])
    check('Spider movement speed 350', spider_cdo.get_editor_property('character_movement').get_editor_property('max_walk_speed') == 350)
    player = unreal.get_default_object(loaded['/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter'].generated_class())
    check('Player movement speed 350', player.get_editor_property('character_movement').get_editor_property('max_walk_speed') == 350)
    check('ThreatClass points to Spider', unreal.get_default_object(loaded['/Game/Anomalies/Containers/BP_AnomalyBox'].generated_class()).get_editor_property('ThreatClass') == spider.generated_class())
    REPORT['spider_components'] = [dict(name=c.get_name(), type=c.get_class().get_name()) for c in A.get_components(spider_cdo)]
    context = loaded['/Game/Core/Input/IMC_Prototype']
    mappings = context.get_editor_property('default_key_mappings').get_editor_property('mappings')
    REPORT['input_mappings'] = [dict(action=m.action.get_name() if m.action else None, key=str(m.key.get_editor_property('key_name'))) for m in mappings]
    for action, key in [('IA_Interact','E'), ('IA_Restart','R')]:
        check(action + ' maps to ' + key, sum(m['action'] == action and m['key'] == key for m in REPORT['input_mappings']) == 1)
    level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    check('Load gameplay map', level.load_level('/Game/Prototype/Maps/L_Prototype'))
    actors = list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
    spawners = [a for a in actors if a.get_class() == loaded['/Game/Anomalies/Containers/BP_BoxSpawner'].generated_class()]
    check('Exactly one placed Spawner', len(spawners) == 1, len(spawners))
    check('No placed gameplay box', not any(a.get_class() == loaded['/Game/Anomalies/Containers/BP_AnomalyBox'].generated_class() for a in actors))
    REPORT['map'] = dict(actor_count=len(actors), spawners=[dict(name=a.get_name(), location=str(a.get_actor_location())) for a in spawners],
                        navigation_actors=[a.get_name() for a in actors if 'NavMesh' in a.get_class().get_name()])
    for dep in registry.get_dependencies('/Game/Prototype/Maps/L_Prototype', options):
        if str(dep).startswith('/Game/') and not ASSETS.does_asset_exist(str(dep)):
            missing_dependencies.append(dict(asset='/Game/Prototype/Maps/L_Prototype', dependency=str(dep)))
    REPORT['missing_direct_game_dependencies'] = missing_dependencies
    check('Core direct hard/soft Game dependencies exist', not missing_dependencies)
    REPORT['status'] = 'PASS' if all(c['passed'] for c in REPORT['checks']) and not REPORT['errors'] else 'FAIL'
    save_report()
    unreal.log('[P0] INSPECTION ' + REPORT['status'])


try:
    main()
except Exception:
    REPORT['status'] = 'FAIL'
    REPORT['errors'].append(traceback.format_exc())
    save_report()
    unreal.log_error('[P0] INSPECTION FAIL: ' + REPORT['errors'][-1])
