"""Generate the T20 map, materials and passive UI. No PIE, MCP or screen control."""
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'Scripts'))
from t20_layout import MAP, LEGACY, UI, ENV, BOX_POINTS, ENTRANCE, START, THREAT_OFFSET, ROOMS, WALLS, COLOURS

OUT = ROOT / 'Saved/T20'
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVEL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
UMG = unreal.get_default_object(unreal.UMGToolSet)
PLAYER = '/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backup():
    destination = OUT / ('AssetsBefore_' + datetime.now().strftime('%Y%m%dT%H%M%S%f'))
    files = [ROOT / 'Content/Prototype/Maps/L_Prototype.umap',
             ROOT / 'Content/FirstPerson/Blueprints/BP_FirstPersonCharacter.uasset',
             ROOT / 'Content/UI/WBP_ExplorationPrompt.uasset']
    files += list((ROOT / 'Content/Prototype/Environment/T20').glob('*.uasset'))
    manifest = {}
    for path in files:
        if not path.exists():
            continue
        target = destination / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        manifest[str(path.relative_to(ROOT))] = digest(path)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'sha256.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return str(destination)


def material(name, rgb, glow=False):
    path = ENV + '/' + name
    asset = ASSETS.load_asset(path) if ASSETS.does_asset_exist(path) else None
    if not asset:
        asset = TOOLS.create_asset(name, ENV, unreal.Material, unreal.MaterialFactoryNew())
    assert asset
    unreal.MaterialEditingLibrary.delete_all_material_expressions(asset)
    colour = unreal.MaterialEditingLibrary.create_material_expression(asset, unreal.MaterialExpressionConstant3Vector)
    colour.set_editor_property('constant', unreal.LinearColor(*rgb, 1.))
    assert unreal.MaterialEditingLibrary.connect_material_property(colour, '', unreal.MaterialProperty.MP_BASE_COLOR)
    if glow:
        assert unreal.MaterialEditingLibrary.connect_material_property(colour, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    rough = unreal.MaterialEditingLibrary.create_material_expression(asset, unreal.MaterialExpressionConstant)
    rough.set_editor_property('r', .75)
    assert unreal.MaterialEditingLibrary.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    unreal.MaterialEditingLibrary.recompile_material(asset)
    assert ASSETS.save_loaded_asset(asset, only_if_is_dirty=False)
    return asset


def actor(cls, label, xyz, yaw=0.):
    obj = ACTORS.spawn_actor_from_class(cls, unreal.Vector(*xyz), unreal.Rotator(pitch=0., yaw=yaw, roll=0.), transient=False)
    assert obj, label
    obj.set_actor_label('T20_' + label)
    obj.set_editor_property('tags', ['T20Generated'])
    return obj


def block(label, xyz, size, mat, collision=True):
    obj = actor(unreal.StaticMeshActor, label, xyz)
    comp = obj.static_mesh_component
    comp.set_static_mesh(CUBE)
    comp.set_material(0, mat)
    obj.set_actor_scale3d(unreal.Vector(*(s / 100. for s in size)))
    comp.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    return obj


def sign(label, content, xyz, yaw=90., size=40., colour=(.8, .9, .87)):
    obj = actor(unreal.TextRenderActor, label, xyz, yaw)
    text = obj.text_render
    text.set_text(unreal.Text(content))
    text.set_world_size(size)
    text.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    text.set_text_render_color(unreal.Color(*(int(v * 255) for v in colour), 255))
    text.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return obj


def light(label, xyz, colour, intensity=4200., radius=1000.):
    obj = actor(unreal.PointLight, label, xyz)
    comp = obj.point_light_component
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_editor_property('intensity', intensity)
    comp.set_editor_property('attenuation_radius', radius)
    comp.set_editor_property('light_color', unreal.Color(*(int(v * 255) for v in colour), 255))


def furniture(name, label, xyz):
    mesh = ASSETS.load_asset('/Game/Prototype/Environment/LowPolyLab/' + name)
    assert mesh, name
    obj = actor(unreal.StaticMeshActor, label, (0., 0., 0.))
    obj.static_mesh_component.set_static_mesh(mesh)
    centre, extent = obj.get_actor_bounds(False)
    obj.set_actor_location(unreal.Vector(xyz[0] - centre.x, xyz[1] - centre.y,
                                       xyz[2] - (centre.z - extent.z)), False, False)
    # Existing imported decorations may lack simple collision. Blockers are explicit cubes.
    obj.static_mesh_component.set_collision_profile_name('NoCollision')


def build_widget():
    bp = ASSETS.load_asset(UI) if ASSETS.does_asset_exist(UI) else None
    if not bp:
        bp = UMG.call_method('CreateWidgetBlueprint', ('/Game/UI', 'WBP_ExplorationPrompt', unreal.AnomalyExplorationWidget.static_class()))
    assert bp
    old = UMG.call_method('GetWidgets', (bp,)).widgets
    if old:
        assert UMG.call_method('RemoveWidget', (bp, old[0].widget))
    root = UMG.call_method('AddWidget', (bp, unreal.CanvasPanel.static_class(), 'ExplorationCanvas', None, -1)).widget
    for name, anchor, position, size, align, font in (
            ('InteractionPrompt', (.5, .5), (0., 50.), (650., 36.), (.5, 0.), 20),
            ('ExplorationObjective', (1., 0.), (-24., 128.), (480., 108.), (1., 0.), 18)):
        item = UMG.call_method('AddWidget', (bp, unreal.TextBlock.static_class(), name, root, -1))
        item.widget.set_text(unreal.Text(''))
        item.widget.set_font_size(font)
        item.widget.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(.78, .93, .85, 1.)))
        item.widget.set_shadow_offset(unreal.Vector2D(1., 1.))
        item.widget.set_shadow_color_and_opacity(unreal.LinearColor(0., 0., 0., 1.))
        item.widget.set_editor_property('justification', unreal.TextJustify.CENTER if name == 'InteractionPrompt' else unreal.TextJustify.RIGHT)
        item.slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(*anchor), maximum=unreal.Vector2D(*anchor)))
        item.slot.set_position(unreal.Vector2D(*position))
        item.slot.set_size(unreal.Vector2D(*size))
        item.slot.set_alignment(unreal.Vector2D(*align))
        UMG.call_method('ToggleWidgetAsVariable', (bp, item.widget, True))
    BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)
    assert bp.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE, bp.get_editor_property('status')
    assert ASSETS.save_loaded_asset(bp, only_if_is_dirty=False)
    return bp


def repair_restart_map():
    """R reloads the current map, including the preserved Legacy map."""
    bp = ASSETS.load_asset(PLAYER)
    graph = unreal.BlueprintEditorLibrary.find_graph(bp, 'T06Restart')
    assert graph
    nodes = BlueprintTools.find_nodes(graph)
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    open_node = next(n for n in nodes if 'OpenLevel' in BlueprintTools._get_node_info(n).type_id)
    get_node = next((n for n in nodes if 'GetCurrentLevelName' in BlueprintTools._get_node_info(n).type_id), None)
    convert = next((n for n in nodes if 'Conv_StringToName' in BlueprintTools._get_node_info(n).type_id), None)
    get_node = get_node or editor.add_call_function_node('/Script/Engine.GameplayStatics:GetCurrentLevelName')
    convert = convert or editor.add_call_function_node('/Script/Engine.KismetStringLibrary:Conv_StringToName')
    def pin(node, name, output=False):
        pins = unreal.BlueprintEditorLibrary.list_output_pins(node) if output else unreal.BlueprintEditorLibrary.list_input_pins(node)
        return next(p for p in pins if str(p.get_pin_name()) == name)
    def same(a, b):
        # Reflected pin wrappers are recreated on enumeration; compare stable node/pin names.
        return a.get_owning_node().get_name() == b.get_owning_node().get_name() and str(a.get_pin_name()) == str(b.get_pin_name())
    def connected(source, target):
        return any(same(p, target) for p in source.list_connected_pins())
    assert pin(get_node, 'bRemovePrefixString').set_pin_value('true')
    open_exec, get_exec, get_then = pin(open_node, 'execute'), pin(get_node, 'execute'), pin(get_node, 'then', True)
    for source in list(open_exec.list_connected_pins()):
        if not same(source, get_then):
            source.break_single_pin_link(open_exec)
            if not connected(source, get_exec):
                assert source.try_create_connection(get_exec)
    if not connected(get_then, open_exec):
        assert get_then.try_create_connection(open_exec)
    for source, target in ((pin(get_node, 'ReturnValue', True), pin(convert, 'InString')),
                           (pin(convert, 'ReturnValue', True), pin(open_node, 'LevelName'))):
        if not connected(source, target):
            assert source.try_create_connection(target)
    BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)
    assert bp.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE, bp.get_editor_property('status')
    assert ASSETS.save_loaded_asset(bp, only_if_is_dirty=False)


OUT.mkdir(parents=True, exist_ok=True)
previous = backup()
protected = [p for folder in ('Anomalies', 'Core', 'Input', 'Interaction', 'UI',
                             'Prototype/Data/Boxes', 'Prototype/Equipment',
                             'Prototype/Environment/LowPolyLab', 'Prototype/Environment/BoxClues')
             for p in (ROOT / 'Content' / folder).rglob('*.uasset')
             if p != ROOT / 'Content/UI/WBP_ExplorationPrompt.uasset']
protected += [ROOT / ('Content/FirstPerson/Blueprints/' + name + '.uasset')
              for name in ('BP_FirstPersonGameMode', 'BP_FirstPersonPlayerController')]
protected += [ROOT / 'Content/Prototype/Maps/L_MainMenu.umap']
before = {str(p.relative_to(ROOT)): digest(p) for p in protected}
assert LEVEL.load_level(MAP)
if not ASSETS.does_asset_exist(LEGACY):
    assert ASSETS.get_metadata_tag(ASSETS.load_asset(MAP), 'T20BuildVersion') != '1', 'Cannot clone exploration as legacy'
    assert LEVEL.new_level_from_template(LEGACY, MAP)
    assert LEVEL.save_current_level()
    assert LEVEL.load_level(MAP)
legacy_file = ROOT / 'Content/Prototype/Maps/L_LegacyPrototype.umap'
legacy_hash = digest(legacy_file)

ui = build_widget()
repair_restart_map()
CUBE = ASSETS.load_asset(ENV + '/SM_LabModuleCube') if ASSETS.does_asset_exist(ENV + '/SM_LabModuleCube') else None
if not CUBE:
    CUBE = ASSETS.duplicate_asset('/Engine/BasicShapes/Cube', ENV + '/SM_LabModuleCube')
assert CUBE and ASSETS.save_loaded_asset(CUBE, only_if_is_dirty=False)
mats = {'Floor': material('M_Floor', (.12, .16, .17)),
        'Wall': material('M_Wall', (.23, .29, .29)),
        'Trim': material('M_Trim', (.045, .065, .07))}
mats.update({key: material('M_' + key, rgb, True) for key, rgb in COLOURS.items()})
for obj in ACTORS.get_all_level_actors():
    label = obj.get_actor_label()
    if label.startswith(('T20_', 'ENV_', 'LIGHT_')) or label == 'PROTOTYPE_CentralPedestal':
        assert ACTORS.destroy_actor(obj)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for name, x0, x1, y0, y1 in ROOMS:
    centre = ((x0+x1)/2., (y0+y1)/2.)
    block(name+'_Floor', (*centre, -10.), (x1-x0, y1-y0, 20), mats['Floor'])
    block(name+'_Ceiling', (*centre, 410.), (x1-x0, y1-y0, 20), mats['Trim'])
    light(name+'_MainLight', (*centre, 340.), (.73, .85, .87), 7000., max(x1-x0, y1-y0))
    block(name+'_CeilingStrip', (*centre, 398.), (120, 20, 3), mats[name], False)
for index, (x, y, width, depth) in enumerate(WALLS):
    block('Wall_%02d' % index, (x, y, 200), (width, depth, 400), mats['Wall'])
    block('Skirt_%02d' % index, (x, y, 20), (width+2, depth+2, 40), mats['Trim'])
# Unbroken green line and arrows lead back toward increasing Y / ENTRY.
block('ReturnLine', (70, 300, .7), (8, 3400, 1), mats['Entry'], False)
for name, x in (('A', -650), ('B', 650)):
    block(name+'_ReturnBranch', (x, 200, .7), (1150, 8, 1), mats['Entry'], False)
for y in (-400, 200, 800, 1350):
    sign('ReturnArrow_%d' % y, '^  ENTRY', (0, y, 2.), yaw=90., size=26., colour=COLOURS['Entry']).set_actor_rotation(unreal.Rotator(pitch=90, yaw=90, roll=0), False)
block('EntryPad', (0, 1700, 1), (650, 460, 2), mats['Entry'], False)
sign('EntryTitle', 'ENTRY / RETURN', (0, 2078, 255), yaw=-90., size=62., colour=COLOURS['Entry'])
sign('EntryGuide', 'A  <    LAB    >  B\nC  STRAIGHT AHEAD', (0, 925, 290), yaw=90., size=31.)
for name, x, yaw in (('A', -240, 0), ('B', 240, 180)):
    block(name+'_PortalHeader', (x, 200, 365), (24, 400, 70), mats['Trim'])
    for y in (0, 400):
        block(name+'_PortalTrim_%d' % y, (x, y, 145), (28, 16, 290), mats[name], False)
    sign(name+'_DoorPlate', name+' / CANDIDATE', (x + (15 if name=='A' else -15), 200, 305), yaw=yaw, size=32., colour=COLOURS[name])
block('C_PortalHeader', (0, -500, 365), (360, 24, 70), mats['Trim'])
sign('C_DoorPlate', 'C / CONTAINMENT', (0, -480, 305), yaw=90., size=32., colour=COLOURS['C'])
sign('HallReturn', 'RETURN  >  ENTRY', (-220, 650, 210), yaw=0., size=28., colour=COLOURS['Entry'])
for index, (name, xyz) in enumerate(zip(('A', 'B', 'C'), BOX_POINTS)):
    x, y, _ = xyz
    block(name+'_Pedestal', (x, y, 20), (75, 75, 20), mats['Trim'])
    block(name+'_CandidateRing', (x, y, 1), (180, 180, 2), mats[name], False)
    sign(name+'_RoomTitle', name+' / SAMPLE BAY', (x, y+340, 270), yaw=90., size=40., colour=COLOURS[name])
    light(name+'_Accent', (x, y, 280), COLOURS[name], 950., 500.)
# Reuse the existing low-poly art; invisible blockers keep decoration collision explicit.
for mesh, label, xyz, size in (
        ('SM_LabDesk', 'EntryDesk', (-580, 1850, 0), (200, 80, 120)),
        ('SM_Shelf_A', 'AShelf', (-1250, 700, 0), (160, 70, 255)),
        ('SM_Locker_A', 'BLocker', (1250, 700, 0), (80, 80, 220))):
    furniture(mesh, label, xyz)
    block(label+'_Collision', (xyz[0], xyz[1], size[2]/2), size, mats['Trim']).set_actor_hidden_in_game(True)
furniture('SM_RetroComputer', 'EntryComputer', (-580, 1850, 122))
spawners = [a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.AnomalyRoundCoordinator)]
assert len(spawners) == 1
spawner = spawners[0]
spawner.set_actor_location(unreal.Vector(), False, False)
spawner.set_actor_rotation(unreal.Rotator(), False)
spawner.set_editor_property('play_mode', unreal.AnomalyPlayMode.EXPLORATION)
spawner.set_editor_property('exploration_widget_class', ui.generated_class())
spawner.set_editor_property('interaction_range', 300.)
spawner.set_editor_property('entrance_location', unreal.Vector(*ENTRANCE))
spawner.set_editor_property('exploration_threat_offset', unreal.Vector(*THREAT_OFFSET))
for prop, xyz in zip(('box_point_left', 'box_point_middle', 'box_point_right'), BOX_POINTS):
    spawner.get_editor_property(prop).set_relative_location(unreal.Vector(*xyz), False, False)
starts = [a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.PlayerStart)]
assert len(starts) == 1
starts[0].set_actor_location(unreal.Vector(*START), False, False)
starts[0].set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), False)
bounds = [a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.NavMeshBoundsVolume)]
assert len(bounds) == 1
bounds[0].set_actor_location(unreal.Vector(0, 300, 150), False, False)
bounds[0].set_actor_scale3d(unreal.Vector(15, 19, 4))
nav = unreal.NavigationSystemV1.get_navigation_system(world)
assert nav
nav.on_navigation_bounds_updated(bounds[0])
for obj in ACTORS.get_all_level_actors():
    if isinstance(obj, unreal.RecastNavMesh):
        obj.set_editor_property('runtime_generation', unreal.RuntimeGenerationType.DYNAMIC)
valid_tiles = unreal.AnomalyRoundCoordinator.build_exploration_navigation(world)
assert valid_tiles > 0, 'Navigation build produced no tiles'
assert not unreal.NavigationSystemV1.is_navigation_being_built(world)
assert LEVEL.save_current_level()
ASSETS.set_metadata_tag(ASSETS.load_asset(MAP), 'T20BuildVersion', '1')
assert LEVEL.save_current_level()
assert digest(legacy_file) == legacy_hash
assert all(digest(ROOT / p) == sha for p, sha in before.items()), 'Protected gameplay/menu assets changed'
report = dict(status='BUILT', backup=previous, map=MAP, legacy_map=LEGACY, legacy_sha256=legacy_hash,
              widget=UI, room_count=len(ROOMS), points=BOX_POINTS, threat_offset=THREAT_OFFSET,
              generated_actors=sum(a.get_actor_label().startswith('T20_') for a in ACTORS.get_all_level_actors()),
              protected_assets_unchanged=len(before), protected_sha256=before,
              navigation='Synchronous native navigation build completed; runtime paths and visible overlay NOT TESTED',
              navigation_valid_tiles=valid_tiles,
              gameplay_tested=False, physical_input='PENDING_MANUAL', visual='NOT RUN',
              scope='T20 Python/C++ build only; no MCP, screen, PIE, gameplay or package')
(OUT / 'build_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('[T20] BUILD PASS')
