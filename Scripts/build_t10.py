"""Add T10 cosmetic motion to the accepted Spider. Asset build only; no PIE/MCP."""
import sys
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'Scripts'))
import build_t05 as t
h, B = t.h, t.B
h.TAG = 'T10_GENERATED'
h.PREFIX = '[T10]'
OUT = ROOT / 'Saved/T10'
FUNCTIONS = ('T10FacePlayer', 'T10AnimateBody')
DEFAULTS = {'T10TurnSpeed': 8.0, 'T10StrideLength': 115.0,
            'T10BobHeight': 2.0, 'T10SwayDegrees': 2.0,
            'T10LeanDegrees': 2.5, 'T10PitchDegrees': 1.0,
            'T10BlendSpeed': 8.0, 'T10MotionScale': 1.0,
            'T10Phase': 0.0, 'T10MoveBlend': 0.0}


def snapshot(bp):
    """Stable pin values/connections of existing gameplay, excluding cosmetic Tick."""
    result = {}
    for g in B.list_graphs(bp):
        if g.get_name() in FUNCTIONS:
            continue
        for n in B.find_nodes(g):
            info = B._get_node_info(n)
            if str(info.type_id).endswith('|ReceiveTick') or str(info.type_id).endswith('|T10FacePlayer') or str(info.type_id).endswith('|T10AnimateBody'):
                continue
            pins = []
            for direction, items in [('in', h.input_pins(n)), ('out', h.output_pins(n))]:
                for p in items:
                    links = sorted(cp.get_owning_node().get_name() + ':' + str(cp.get_pin_name())
                                   for cp in p.list_connected_pins())
                    pins.append([direction, str(p.get_pin_name()), str(p.get_pin_value()), links])
            result[g.get_name() + '/' + n.get_name()] = [str(info.type_id), pins]
    return result


def hashes():
    from prepare_t07 import PACKAGES
    result = {}
    for name in PACKAGES:
        path = ROOT / 'Content' / (name + ('.umap' if name.endswith('/L_Prototype') else '.uasset'))
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def editor(g):
    return unreal.BlueprintGraphEditor.get_graph_editor(g)


def native(g, name, library='KismetMathLibrary', **inputs):
    n = h._tag(editor(g).add_call_function_node('/Script/Engine.' + library + ':' + name))
    assert n, name
    # UE promotes arithmetic operators from their first typed connection.
    # Connect typed values before assigning literals to avoid a wrong overload.
    for pin, value in sorted(inputs.items(), key=lambda item: not isinstance(item[1], tuple)):
        feed(n, pin, value)
    return n


def feed(n, pin, value):
    if isinstance(value, tuple):
        t.wire(value[0], value[1], n, pin)
    else:
        t.val(n, pin, value)


def ret(n):
    return n, 'ReturnValue'


def math(g, name, **inputs):
    return ret(native(g, name, **inputs))


def get(g, name):
    return h._tag(t.getter(g, name)), name


def setvar(g, name, value, previous):
    n = h._tag(editor(g).add_set_member_variable_node(name))
    feed(n, name, value)
    t.wire(previous, 'then', n, 'execute')
    return n


def sequence(g, previous, n):
    t.wire(previous, 'then', n, 'execute')
    return n


def schema(bp):
    marker = h.ASSETS.get_metadata_tag(bp, 'T10Schema')
    vector_type = unreal.BlueprintEditorLibrary.get_struct_type(unreal.Vector.static_struct())
    if marker == '2':
        return False
    if marker == '1':
        unreal.BlueprintEditorLibrary.change_member_variable_type(bp, 'T10BaseLocation', vector_type)
        h.ASSETS.set_metadata_tag(bp, 'T10Schema', '2')
        t.compile_bp(bp, True)
        unreal.log('[T10] SCHEMA PASS - reload corrected Vector schema')
        return True
    assert not any(g.get_name() in FUNCTIONS for g in B.list_graphs(bp)), 'Unrecognized T10 graphs'
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'Content/Anomalies/Creatures/BP_Spider.uasset'
    backup = OUT / ('BP_Spider_before_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.uasset')
    shutil.copy2(source, backup)
    visual = next(c for c in t.components(bp) if 'AlienVisual' in c.get_name())
    loc = visual.get_editor_property('relative_location')
    rot = visual.get_editor_property('relative_rotation')
    assert abs(rot.pitch) + abs(rot.yaw) + abs(rot.roll) < .001, 'Review nonzero base rotation'
    baseline = {'backup': str(backup), 'gameplay': snapshot(bp), 'hashes': hashes(),
                'base_location': [loc.x, loc.y, loc.z]}
    (OUT / 'baseline.json').write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding='utf-8')
    for name in DEFAULTS:
        h.ensure_variable(bp, name, unreal.BlueprintEditorLibrary.get_basic_type_by_name('real'),
                          name not in ('T10Phase', 'T10MoveBlend'))
    h.ensure_variable(bp, 'T10BaseLocation', vector_type)
    for name in FUNCTIONS:
        g = B.add_function_graph(bp, name)
        if g.get_name() != name:
            unreal.BlueprintEditorLibrary.rename_graph(g, name)
        editor(g).add_graph_input_parameter('DeltaSeconds', unreal.BlueprintEditorLibrary.get_basic_type_by_name('real'))
    h.ASSETS.set_metadata_tag(bp, 'T10Schema', '2')
    t.compile_bp(bp, True)
    unreal.log('[T10] SCHEMA PASS - reload for graph construction')
    return True


def face(g):
    entry = h.entry_node(g)
    player = native(g, 'GetPlayerCharacter', 'GameplayStatics')
    valid = t.valid_branch(g, entry, 'then', player, 'ReturnValue')
    here = native(g, 'K2_GetActorLocation', 'Actor')
    there = native(g, 'K2_GetActorLocation', 'Actor', self=ret(player))
    delta = math(g, 'Subtract_VectorVector', A=ret(there), B=ret(here))
    distance = math(g, 'VSizeXY', A=delta)
    nonzero = math(g, 'Greater_DoubleDouble', A=distance, B=1.0)
    guard = t.branch(g, valid, 'then', nonzero)
    look = native(g, 'FindLookAtRotation', Start=ret(here), Target=ret(there))
    split = native(g, 'BreakRotator', InRot=ret(look))
    yaw = native(g, 'MakeRotator', Roll=0.0, Pitch=0.0, Yaw=(split, 'Yaw'))
    current = native(g, 'K2_GetActorRotation', 'Actor')
    smooth = native(g, 'RInterpTo', Current=ret(current), Target=ret(yaw),
                    DeltaTime=(entry, 'DeltaSeconds'), InterpSpeed=get(g, 'T10TurnSpeed'))
    apply = native(g, 'K2_SetActorRotation', 'Actor', NewRotation=ret(smooth), bTeleportPhysics=False)
    t.wire(guard, 'then', apply, 'execute')


def animate(g):
    entry = h.entry_node(g)
    visual = get(g, 'AlienVisual')
    valid = t.valid_branch(g, entry, 'then', visual[0], visual[1])
    velocity = native(g, 'GetVelocity', 'Actor')
    speed = math(g, 'VSizeXY', A=ret(velocity))
    fraction = math(g, 'Divide_DoubleDouble', A=math(g, 'Subtract_DoubleDouble', A=speed, B=5.0), B=345.0)
    target = math(g, 'FClamp', Value=fraction, Min=0.0, Max=1.0)
    smooth = math(g, 'FInterpTo', Current=get(g, 'T10MoveBlend'), Target=target,
                  DeltaTime=(entry, 'DeltaSeconds'), InterpSpeed=get(g, 'T10BlendSpeed'))
    blend_set = setvar(g, 'T10MoveBlend', smooth, valid)
    stride = math(g, 'FMax', A=get(g, 'T10StrideLength'), B=10.0)
    distance = math(g, 'Multiply_DoubleDouble', A=speed, B=(entry, 'DeltaSeconds'))
    advance = math(g, 'Multiply_DoubleDouble', A=math(g, 'Divide_DoubleDouble', A=distance, B=stride), B=6.28318530718)
    modulo = native(g, 'FMod', Dividend=math(g, 'Add_DoubleDouble', A=get(g, 'T10Phase'), B=advance), Divisor=6.28318530718)
    phase = modulo, 'Remainder'
    phase_set = setvar(g, 'T10Phase', phase, blend_set)
    strength = math(g, 'Multiply_DoubleDouble', A=get(g, 'T10MoveBlend'),
                    B=math(g, 'FClamp', Value=get(g, 'T10MotionScale'), Min=0.0, Max=1.0))
    wave = math(g, 'Sin', A=get(g, 'T10Phase'))
    double_phase = math(g, 'Multiply_DoubleDouble', A=get(g, 'T10Phase'), B=2.0)
    bounce = math(g, 'Multiply_DoubleDouble', A=math(g, 'Subtract_DoubleDouble', A=1.0,
                  B=math(g, 'Cos', A=double_phase)), B=0.5)
    bob = math(g, 'Multiply_DoubleDouble', A=bounce, B=get(g, 'T10BobHeight'))
    # Small positive lift offsets minor body tilt; no collision/capsule movement.
    lift = math(g, 'Multiply_DoubleDouble', A=math(g, 'Add_DoubleDouble', A=bob, B=0.8), B=strength)
    offset = math(g, 'MakeVector', X=0.0, Y=0.0, Z=lift)
    location = math(g, 'Add_VectorVector', A=get(g, 'T10BaseLocation'), B=offset)
    roll = math(g, 'Multiply_DoubleDouble', A=math(g, 'Multiply_DoubleDouble', A=wave,
                B=get(g, 'T10SwayDegrees')), B=strength)
    nod = math(g, 'Multiply_DoubleDouble', A=math(g, 'Sin', A=double_phase), B=get(g, 'T10PitchDegrees'))
    pitch = math(g, 'Multiply_DoubleDouble', A=math(g, 'Subtract_DoubleDouble', A=nod,
                 B=get(g, 'T10LeanDegrees')), B=strength)
    rotation = math(g, 'MakeRotator', Roll=roll, Pitch=pitch, Yaw=0.0)
    apply = native(g, 'K2_SetRelativeLocationAndRotation', 'SceneComponent', self=visual,
                   NewLocation=location, NewRotation=rotation, bSweep=False, bTeleport=False)
    sequence(g, phase_set, apply)


def main():
    bp = h.load(t.SPIDER)
    if h.ASSETS.get_metadata_tag(bp, 'T10BuildVersion') == '1':
        t.compile_bp(bp)
        unreal.log('[T10] BUILD PASS - existing build retained')
        return
    if schema(bp):
        return
    for name, builder in zip(FUNCTIONS, (face, animate)):
        g = next(g for g in B.list_graphs(bp) if g.get_name() == name)
        assert len(B.find_nodes(g)) <= 2, 'Refusing to overwrite nonempty function'
        builder(g)
        for index, n in enumerate(B.find_nodes(g)):
            n.set_node_pos(unreal.IntPoint((index % 7) * 330, (index // 7) * 240))
    g = unreal.BlueprintEditorLibrary.find_event_graph(bp)
    ticks = [n for n in B.find_nodes(g) if str(B._get_node_info(n).type_id).endswith('|ReceiveTick')]
    assert len(ticks) <= 1
    tick = ticks[0] if ticks else B.add_event(bp, 'ReceiveTick')
    assert not h.find_pin(tick, 'out', ['then']).list_connected_pins(), 'Existing Tick logic requires review'
    guard = t.branch(g, tick, variable='bResolved')
    first = t.node(g, FUNCTIONS[0])
    second = t.node(g, FUNCTIONS[1])
    t.wire(guard, 'else', first, 'execute')
    t.wire(first, 'then', second, 'execute')
    for n in (first, second):
        t.wire(tick, 'DeltaSeconds', n, 'DeltaSeconds')
    for index, n in enumerate((tick, guard, first, second)):
        n.set_node_pos(unreal.IntPoint(index * 350, 3500))
    t.compile_bp(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    for name, value in DEFAULTS.items():
        cdo.set_editor_property(name, value)
    baseline = json.loads((OUT / 'baseline.json').read_text(encoding='utf-8'))
    cdo.set_editor_property('T10BaseLocation', unreal.Vector(*baseline['base_location']))
    cdo.set_editor_property('use_controller_rotation_yaw', False)
    move = cdo.get_editor_property('character_movement')
    move.set_editor_property('orient_rotation_to_movement', False)
    move.set_editor_property('use_controller_desired_rotation', False)
    tick_settings = cdo.get_editor_property('primary_actor_tick')
    tick_settings.set_editor_property('start_with_tick_enabled', True)
    tick_settings.set_editor_property('tick_interval', 0.0)
    cdo.set_editor_property('primary_actor_tick', tick_settings)
    current = snapshot(bp)
    assert {key: current.get(key) for key in baseline['gameplay']} == baseline['gameplay'], 'Existing gameplay graph changed'
    h.ASSETS.set_metadata_tag(bp, 'T10BuildVersion', '1')
    t.compile_bp(bp, True)
    unreal.log('[T10] BUILD PASS - BP_Spider saved; runtime acceptance NOT RUN')


if __name__ == '__main__':
    main()
