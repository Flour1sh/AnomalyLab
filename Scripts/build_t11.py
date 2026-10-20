"""Staged T11 asset build through local Unreal Python; never MCP, PIE or UI."""
import sys
import json
import hashlib
import shutil
import traceback
from pathlib import Path
from datetime import datetime
import unreal

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'Scripts'))
import build_t05 as t
from t11_data import FIELDS, ROWS, validate_rows
h, B = t.h, t.B
h.TAG, h.PREFIX = 'T11_GENERATED', '[T11]'
OUT = ROOT/'Saved/T11'
DEFINITION = '/Game/Prototype/Data/Boxes/BP_AnomalyBoxDefinition'
DATA_DIR = '/Game/Prototype/Data/Boxes'
FUNCTIONS = ('T11InitializeDefinition', 'T11LoadDefinition', 'T11ValidateDefinition', 'T11RollOutcome', 'T11RollReward')


def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('Content', 'Config') for p in (ROOT/folder).rglob('*') if p.is_file()} | {
                '我的项目3.uproject': hashlib.sha256((ROOT/'我的项目3.uproject').read_bytes()).hexdigest()}


def backup():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'baseline.json').exists():
        return
    source = ROOT/'Content/Anomalies/Containers/BP_AnomalyBox.uasset'
    dest = OUT/('Backup_'+datetime.now().strftime('%Y%m%dT%H%M%S'))/source.name
    dest.parent.mkdir(parents=True)
    shutil.copy2(source, dest)
    (OUT/'baseline.json').write_text(json.dumps(dict(backup=str(dest), hashes=hashes()), ensure_ascii=False, indent=2), encoding='utf-8')


def create_data():
    validate_rows(ROWS)
    assets = unreal.AssetToolsHelpers.get_asset_tools()
    if not h.ASSETS.does_asset_exist(DEFINITION):
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.PrimaryDataAsset.static_class())
        definition = assets.create_asset('BP_AnomalyBoxDefinition', DATA_DIR, unreal.Blueprint, factory)
        for name, kind in FIELDS.items():
            h.ensure_variable(definition, name, unreal.BlueprintEditorLibrary.get_basic_type_by_name(kind), True)
        t.compile_bp(definition, True)
        unreal.log('[T11] DATA SCHEMA PASS - reload before creating definition instances')
        return None, None
    definition = h.load(DEFINITION)
    cls = definition.generated_class()
    rows = {}
    for row in ROWS:
        path = DATA_DIR+'/DA_Box_'+row['Name']
        if h.ASSETS.does_asset_exist(path):
            obj = h.load(path)
        else:
            factory = unreal.DataAssetFactory()
            factory.set_editor_property('data_asset_class', cls)
            obj = assets.create_asset('DA_Box_'+row['Name'], DATA_DIR, cls, factory)
            for name in FIELDS:
                obj.set_editor_property(name, row[name])
            assert h.ASSETS.save_loaded_asset(obj, only_if_is_dirty=False)
        rows[row['Name']] = obj
    (OUT/'definitions.json').write_text(json.dumps(ROWS,ensure_ascii=False,indent=2),encoding='utf-8')
    return definition, rows


def schema(bp, s):
    if h.ASSETS.get_metadata_tag(bp, 'T11Schema') == '1':
        return False
    for name, kind, editable in (
        ('DefinitionID','name',True), ('ResolvedDefinitionID','name',False),
        ('bDefinitionInitialized','bool',False), ('bDefinitionValid','bool',False),
        ('DefinitionRoll','int',False), ('WeightedOutcomeRoll','real',False),
        ('bUseFixedSeeds','bool',True), ('ConfigurationSeed','int',True), ('OutcomeSeed','int',True)):
        h.ensure_variable(bp, name, unreal.BlueprintEditorLibrary.get_basic_type_by_name(kind), editable)
    h.ensure_variable(bp, 'DefinitionAsset', unreal.BlueprintEditorLibrary.get_object_reference_type(s.generated_class()), False)
    for name, kind in FIELDS.items():
        h.ensure_variable(bp, 'Data'+name, unreal.BlueprintEditorLibrary.get_basic_type_by_name(kind), False)
    for name in ('ConfigurationStream','OutcomeStream'):
        h.ensure_variable(bp, name, unreal.BlueprintEditorLibrary.get_struct_type(unreal.RandomStream.static_struct()), False)
    for name in FUNCTIONS:
        g = B.add_function_graph(bp, name)
        if g.get_name() != name:
            unreal.BlueprintEditorLibrary.rename_graph(g, name)
    h.ASSETS.set_metadata_tag(bp, 'T11Schema', '1')
    t.compile_bp(bp, True)
    unreal.log('[T11] SCHEMA PASS - reload required for graph construction')
    return True


def ed(g):
    return unreal.BlueprintGraphEditor.get_graph_editor(g)


def feed(n, pin, value):
    if isinstance(value, tuple):
        t.wire(value[0], value[1], n, pin)
    else:
        t.val(n, pin, value)


def native(g, name, library='KismetMathLibrary', **inputs):
    n = h._tag(ed(g).add_call_function_node('/Script/Engine.'+library+':'+name))
    assert n, name
    for pin, value in sorted(inputs.items(), key=lambda x: not isinstance(x[1], tuple)):
        feed(n, pin, value)
    return n


def math(g, name, **inputs):
    return native(g, name, **inputs), 'ReturnValue'


def get(g, name):
    return h._tag(t.getter(g, name)), name


def put(g, name, value, previous, pin='then'):
    n = h._tag(ed(g).add_set_member_variable_node(name))
    feed(n, name, value)
    t.wire(previous, pin, n, 'execute')
    return n


def call(g, name, previous, pin='then'):
    return t.call(g, name, previous, pin)


def data_break(g):
    return g


def field(g, name):
    return get(g, 'Data'+name)


def initialize(g):
    entry = h.entry_node(g)
    guard = t.branch(g, entry, variable='bDefinitionInitialized')
    once = put(g, 'bDefinitionInitialized', True, guard, 'else')
    fixed = t.branch(g, once, variable='bUseFixedSeeds')
    tails = []
    for pin, random_seed in [('then',False), ('else',True)]:
        prev, prev_pin = fixed, pin
        for stream, seed in [('ConfigurationStream','ConfigurationSeed'),('OutcomeStream','OutcomeSeed')]:
            source = math(g,'RandomIntegerInRange',Min=1,Max=2147483646) if random_seed else get(g,seed)
            value = math(g,'MakeRandomStream',InitialSeed=source)
            prev = put(g, stream, value, prev, prev_pin)
            prev_pin = 'then'
        tails.append(prev)
    empty = math(g,'EqualEqual_NameName',A=get(g,'DefinitionID'),B='None')
    choose = t.branch(g,tails[0],condition=empty)
    t.wire(tails[1],'then',choose,'execute')
    roll = put(g,'DefinitionRoll',math(g,'RandomIntegerInRangeFromStream',Stream=get(g,'ConfigurationStream'),Min=0,Max=2),choose)
    equal0 = math(g,'EqualEqual_IntInt',A=get(g,'DefinitionRoll'),B=0)
    equal1 = math(g,'EqualEqual_IntInt',A=get(g,'DefinitionRoll'),B=1)
    other = math(g,'SelectName',A='Risky',B='Unknown',bPickA=equal1)
    name = math(g,'SelectName',A='Safe',B=other,bPickA=equal0)
    random_name = put(g,'ResolvedDefinitionID',name,roll)
    explicit_name = put(g,'ResolvedDefinitionID',get(g,'DefinitionID'),choose,'else')
    load = call(g,'T11LoadDefinition',random_name)
    t.wire(explicit_name,'then',load,'execute')
    b = data_break(g)
    hidden = t.branch(g,load,condition=field(b,'RandomHiddenProfile'))
    roll_hidden = put(g,'DefinitionRoll',math(g,'RandomIntegerInRangeFromStream',Stream=get(g,'ConfigurationStream'),Min=0,Max=2),hidden)
    name = math(g,'SelectName',A='UnknownSafe',
                B=math(g,'SelectName',A='UnknownMedium',B='UnknownRisky',bPickA=math(g,'EqualEqual_IntInt',A=get(g,'DefinitionRoll'),B=1)),
                bPickA=math(g,'EqualEqual_IntInt',A=get(g,'DefinitionRoll'),B=0))
    hidden_name = put(g,'ResolvedDefinitionID',name,roll_hidden)
    call(g,'T11LoadDefinition',hidden_name)


def load_definition(g, definitions):
    previous = put(g,'bDefinitionValid',False,h.entry_node(g))
    previous_pin = 'then'
    ready = []
    for name, obj in definitions.items():
        match = t.branch(g, previous, previous_pin, condition=math(g,'EqualEqual_NameName',A=get(g,'ResolvedDefinitionID'),B=name))
        ready.append(put(g,'DefinitionAsset',obj.get_path_name(),match))
        previous, previous_pin = match, 'else'
    t.print_after(g,previous,previous_pin,'[Box] ERROR T11 definition ID missing; box cannot open')
    cls_path = h.load(DEFINITION).generated_class().get_path_name()
    # References are constants to project-owned assets, but still validate before reading.
    valid = t.valid_branch(g,ready[0],'then',*get(g,'DefinitionAsset'))
    for tail in ready[1:]:
        t.wire(tail,'then',valid,'execute')
    prev = valid
    for name in FIELDS:
        n = h._tag(ed(g).add_get_member_variable_node(name, cls_path))
        feed(n,'self',get(g,'DefinitionAsset'))
        prev = put(g,'Data'+name,(n,name),prev)
    call(g,'T11ValidateDefinition',prev)
    t.print_after(g,valid,'else','[Box] ERROR T11 definition asset missing; box cannot open')


def validate_definition(g):
    b = data_break(g)
    checks = []
    for name in ('HighValueChance','TrashChance','ThreatChance','ScanProbabilityError','MetalChance','WarningChance','WearChance'):
        checks.extend([math(g,'GreaterEqual_DoubleDouble',A=field(b,name),B=0.0), math(g,'LessEqual_DoubleDouble',A=field(b,name),B=1.0)])
    total = math(g,'Add_DoubleDouble',A=math(g,'Add_DoubleDouble',A=field(b,'HighValueChance'),B=field(b,'TrashChance')),B=field(b,'ThreatChance'))
    delta = math(g,'Abs',A=math(g,'Subtract_DoubleDouble',A=total,B=1.0))
    checks.extend([math(g,'LessEqual_DoubleDouble',A=delta,B=0.000001),
                   math(g,'GreaterEqual_IntInt',A=field(b,'ValueMin'),B=0),
                   math(g,'GreaterEqual_IntInt',A=field(b,'ValueMax'),B=field(b,'ValueMin')),
                   math(g,'LessEqual_IntInt',A=field(b,'ValueMax'),B=2147483646),
                   math(g,'GreaterEqual_DoubleDouble',A=field(b,'ValueLowerScale'),B=0.0),
                   math(g,'LessEqual_DoubleDouble',A=field(b,'ValueLowerScale'),B=1.0),
                   math(g,'GreaterEqual_DoubleDouble',A=field(b,'ValueUpperScale'),B=1.0)])
    result = checks[0]
    for other in checks[1:]:
        result = math(g,'BooleanAND',A=result,B=other)
    store = put(g,'bDefinitionValid',result,h.entry_node(g))
    guard = t.branch(g,store,variable='bDefinitionValid')
    t.print_after(g,guard,'else','[Box] ERROR T11 invalid definition; box cannot open')


def roll_outcome(g):
    guard = t.branch(g,h.entry_node(g),variable='bDefinitionValid')
    roll = put(g,'WeightedOutcomeRoll',math(g,'RandomFloatFromStream',Stream=get(g,'OutcomeStream')),guard)
    b = data_break(g)
    high = t.branch(g,roll,condition=math(g,'Less_DoubleDouble',A=get(g,'WeightedOutcomeRoll'),B=field(b,'HighValueChance')))
    put(g,'OutcomeRoll',0,high)
    threshold = math(g,'Add_DoubleDouble',A=field(b,'HighValueChance'),B=field(b,'TrashChance'))
    trash = t.branch(g,high,'else',condition=math(g,'Less_DoubleDouble',A=get(g,'WeightedOutcomeRoll'),B=threshold))
    put(g,'OutcomeRoll',1,trash)
    put(g,'OutcomeRoll',2,trash,'else')


def roll_reward(g):
    guard = t.branch(g,h.entry_node(g),variable='bDefinitionValid')
    b = data_break(g)
    value = math(g,'RandomIntegerInRangeFromStream',Stream=get(g,'OutcomeStream'),Min=field(b,'ValueMin'),Max=field(b,'ValueMax'))
    put(g,'HighValueAmount',value,guard)


def insert_before(g, target, function):
    target_pin = h.find_pin(target,'in',['execute'])
    sources = list(target_pin.list_connected_pins())
    assert len(sources) == 1
    source = sources[0]
    unreal.BlueprintGraphPinLibrary.break_single_pin_link(source,target_pin)
    n = t.node(g,function)
    assert source.try_create_connection(h.find_pin(n,'in',['execute']))
    t.wire(n,'then',target,'execute')
    return n


def patch_event(bp):
    g = unreal.BlueprintEditorLibrary.find_event_graph(bp)
    nodes = B.find_nodes(g)
    types = lambda suffix: [n for n in nodes if str(B._get_node_info(n).type_id).endswith('|'+suffix)]
    # Reject invalid definitions before setting bOpened or announcing a selection.
    opened = types('SetbOpened')
    assert len(opened) == 1
    initialize_call = insert_before(g,opened[0],'T11InitializeDefinition')
    unreal.BlueprintGraphPinLibrary.break_single_pin_link(h.find_pin(initialize_call,'out',['then']),h.find_pin(opened[0],'in',['execute']))
    valid = t.branch(g,initialize_call,variable='bDefinitionValid')
    t.wire(valid,'then',opened[0],'execute')
    # BeginPlay fixes hidden parameters before the player can inspect or scan.
    assert not types('ReceiveBeginPlay')
    begin = B.add_event(bp,'ReceiveBeginPlay')
    call(g,'T11InitializeDefinition',begin)
    sets = types('SetOutcomeRoll')
    assert len(sets) == 1
    old_set = sets[0]
    old_random = h.find_pin(old_set,'in',['OutcomeRoll']).list_connected_pins()[0].get_owning_node()
    old_switch = h.find_pin(old_set,'out',['then']).list_connected_pins()[0].get_owning_node()
    replacement = insert_before(g,old_set,'T11RollOutcome')
    ed(g).remove_nodes([old_set,old_random])
    t.wire(replacement,'then',old_switch,'execute')
    t.wire(*get(g,'OutcomeRoll'),old_switch,'Selection')
    # Cache the reward once on each HighValue path, before visual spawning.
    forced = next(n for n in nodes if n.get_name() == 'K2Node_SwitchEnum_9')
    for switch, pin in ((forced,'NewEnumerator0'),(old_switch,'0')):
        target = h.find_pin(switch,'out',[pin]).list_connected_pins()[0].get_owning_node()
        insert_before(g,target,'T11RollReward')


def build_graphs(bp, dt):
    if h.ASSETS.get_metadata_tag(bp,'T11BuildVersion') == '1':
        if h.ASSETS.get_metadata_tag(bp,'T11LayoutVersion') != '1':
            B.arrange_nodes(B.find_nodes(unreal.BlueprintEditorLibrary.find_event_graph(bp)))
            h.ASSETS.set_metadata_tag(bp,'T11LayoutVersion','1')
            t.compile_bp(bp,True)
        (OUT/'build.json').write_text(json.dumps(dict(status='BUILD PASS',runtime='NOT RUN',
            assets=[DEFINITION]+[o.get_path_name() for o in dt.values()]+[h.BOX_PATH],hashes=hashes()),ensure_ascii=False,indent=2),encoding='utf-8')
        unreal.log('[T11] BUILD PASS - existing completed build retained')
        return
    builders = (initialize, lambda g: load_definition(g,dt), validate_definition, roll_outcome, roll_reward)
    for name, builder in zip(FUNCTIONS, builders):
        g = next(g for g in B.list_graphs(bp) if g.get_name() == name)
        assert len(B.find_nodes(g)) <= 2, 'Refusing to replace nonempty '+name
        builder(g)
        B.arrange_nodes(B.find_nodes(g))
    patch_event(bp)
    B.arrange_nodes(B.find_nodes(unreal.BlueprintEditorLibrary.find_event_graph(bp)))
    t.compile_bp(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    for name, value in dict(DefinitionID='None',ResolvedDefinitionID='None',
                           bDefinitionInitialized=False,bDefinitionValid=False,bUseFixedSeeds=False,
                           ConfigurationSeed=11001,OutcomeSeed=11002,bForceOutcome=False,
                           HighValueAmount=0,TrashAmount=3).items():
        cdo.set_editor_property(name,value)
    h.ASSETS.set_metadata_tag(bp,'T11BuildVersion','1')
    h.ASSETS.set_metadata_tag(bp,'T11LayoutVersion','1')
    t.compile_bp(bp,True)
    (OUT/'build.json').write_text(json.dumps(dict(status='BUILD PASS',runtime='NOT RUN',
        assets=[DEFINITION]+[o.get_path_name() for o in dt.values()]+[h.BOX_PATH],hashes=hashes()),ensure_ascii=False,indent=2),encoding='utf-8')
    unreal.log('[T11] BUILD PASS - assets compiled and saved; gameplay tests NOT RUN')


def main():
    backup()
    s, dt = create_data()
    if s is None:
        return
    bp = h.load(h.BOX_PATH)
    if schema(bp, s):
        return
    build_graphs(bp, dt)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        (OUT/'build_error.txt').write_text(traceback.format_exc(), encoding='utf-8')
        unreal.log_error('[T11] FAIL '+traceback.format_exc())
