"""Staged native-parent migration of existing project Blueprints. Logs and backups are mandatory."""
import json
import sys
import traceback
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'Scripts'))
from cpp_migration import context, journal, write
from t11_data import FIELDS, ROWS
from editor_toolset.toolsets.blueprint import BlueprintTools as B
from editor_toolset.toolsets.actor import ActorTools as A
import build_t04 as h
import build_t05 as t

RUN = context()
OUT = Path(RUN['directory'])
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
BOX = h.BOX_PATH
WALLET = h.WALLET_PATH
SPAWNER = '/Game/Anomalies/Containers/BP_BoxSpawner'
SPIDER = '/Game/Anomalies/Creatures/BP_Spider'
DEFINITION = '/Game/Prototype/Data/Boxes/BP_AnomalyBoxDefinition'
PATHS = [DEFINITION, WALLET, BOX, SPIDER, SPAWNER, h.CHARACTER_PATH, h.HUD_PATH, h.INTERACTION_PATH]
REPORT = dict(phase=RUN['asset_phase'], status='RUNNING', modified_assets=[], checks=[], errors=[])


def load(path):
    asset = ASSETS.load_asset(path)
    assert asset, path
    return asset


def compile_save(bp):
    B.compile_blueprint(bp, warnings_as_errors=True)
    assert all(not unreal.BlueprintGraphEditor.get_graph_editor(g).list_nodes_with_errors() for g in B.list_graphs(bp))
    assert ASSETS.save_loaded_asset(bp, only_if_is_dirty=False)
    REPORT['modified_assets'].append(bp.get_path_name().split('.')[0])
    journal(RUN, 'asset_saved', asset=bp.get_path_name(), phase=REPORT['phase'])


def value(v):
    if v is None or isinstance(v, (bool,int,float,str)): return v
    if isinstance(v,unreal.Object): return {'object':v.get_path_name()}
    return str(v)


def export():
    result = {}
    for path in PATHS:
        bp=load(path); cdo=unreal.get_default_object(bp.generated_class())
        defaults={str(n):value(cdo.get_editor_property(str(n))) for n in B.list_variables(bp)}
        graphs={}
        for g in B.list_graphs(bp):
            graphs[g.get_name()]=[dict(name=n.get_name(),type=str(B._get_node_info(n).type_id),
                                     pins=[dict(name=str(p.get_pin_name()),value=str(p.get_pin_value()),
                                                links=[q.get_owning_node().get_name()+'.'+str(q.get_pin_name()) for q in p.list_connected_pins()])
                                           for p in h.input_pins(n)+h.output_pins(n)]) for n in B.find_nodes(g)]
        components=[]
        for c in (A.get_components(cdo) if isinstance(cdo,unreal.Actor) else []):
            d=dict(name=c.get_name(),type=c.get_class().get_name())
            for prop in ('relative_location','relative_rotation','relative_scale3d','static_mesh','skeletal_mesh'):
                try: d[prop]=value(c.get_editor_property(prop))
                except Exception: pass
            components.append(d)
        result[path]=dict(defaults=defaults,graphs=graphs,components=components,parent=bp.get_blueprint_parent_class().get_path_name())
    result['definitions']=ROWS
    write(OUT/'pre_migration_assets.json',result)
    journal(RUN,'blueprint_baseline_exported',assets=PATHS)


def clear_graph(g):
    nodes=list(B.find_nodes(g))
    if nodes: unreal.BlueprintGraphEditor.get_graph_editor(g).remove_nodes(nodes)


def remove_variables(bp, names):
    existing=set(str(n) for n in B.list_variables(bp))
    graphs=list(B.list_graphs(bp))
    g=unreal.BlueprintEditorLibrary.find_event_graph(bp) or (graphs[0] if graphs else None)
    assert g or not (existing & set(names)), 'No graph editor to remove variables'
    for name in names:
        if name in existing:
            assert unreal.BlueprintGraphEditor.get_graph_editor(g).remove_member_variable(name), name


def parent(bp, cls):
    B.set_parent(bp,cls)


def event(bp, name):
    return B.add_event(bp,name)


def node(g, name):
    return t.node(g,name)


def native(g, cls, name):
    n=unreal.BlueprintGraphEditor.get_graph_editor(g).add_call_function_node('/Script/AnomalyLab.'+cls+':'+name)
    assert n, name
    return n


def wire(a, ap, b, bp):
    h.connect(a,[ap],b,[bp])


def forward(bp, event_name, dispatcher, arguments):
    g=unreal.BlueprintEditorLibrary.find_event_graph(bp)
    e=event(bp,event_name)
    n=node(g,'Call'+dispatcher)
    wire(e,'then',n,'execute')
    for arg in arguments: wire(e,arg,n,arg)


def outcome_forward(bp, event_name, dispatcher):
    g=unreal.BlueprintEditorLibrary.find_event_graph(bp)
    e=event(bp,event_name)
    editor=unreal.BlueprintGraphEditor.get_graph_editor(g)
    prev,prev_pin=e,'then'
    for i in range(3):
        eq=editor.add_call_function_node('/Script/Engine.KismetMathLibrary:EqualEqual_IntInt')
        wire(e,'OutcomeIndex',eq,'A');t.val(eq,'B',i)
        branch=t.branch(g,prev,prev_pin,condition=(eq,'ReturnValue'))
        n=node(g,'Call'+dispatcher)
        wire(branch,'then',n,'execute')
        t.val(n,'Outcome','NewEnumerator'+str(i))
        wire(e,'SpawnedActor',n,'SpawnedActor');wire(e,'bSpawnSucceeded',n,'bSpawnSucceeded')
        prev,prev_pin=branch,'else'


def definition():
    bp=load(DEFINITION)
    if ASSETS.get_metadata_tag(bp,'CppMigrationVersion')=='1': return
    remove_variables(bp,list(FIELDS))
    parent(bp,unreal.AnomalyBoxDefinition.static_class())
    ASSETS.set_metadata_tag(bp,'CppMigrationVersion','1')
    compile_save(bp)


def configure_data():
    for row in ROWS:
        obj=load('/Game/Prototype/Data/Boxes/DA_Box_'+row['Name'])
        assert isinstance(obj,unreal.AnomalyBoxDefinition), obj
        for key in FIELDS: obj.set_editor_property(key,row[key])
        assert ASSETS.save_loaded_asset(obj, only_if_is_dirty=False)
        REPORT['modified_assets'].append(obj.get_path_name().split('.')[0])
    journal(RUN,'native_definitions_configured',count=len(ROWS))


def wallet():
    bp=load(WALLET)
    if ASSETS.get_metadata_tag(bp,'CppMigrationVersion')=='1': return
    # Keep legacy callable signatures and dispatcher used by the Character; replace their bodies.
    add=next(g for g in B.list_graphs(bp) if g.get_name()=='AddMoney')
    get=next(g for g in B.list_graphs(bp) if g.get_name()=='GetMoney')
    reset=next(g for g in B.list_graphs(bp) if g.get_name()=='ResetMoney')
    for g in (add,get,reset):
        keep=[n for n in B.find_nodes(g) if isinstance(n,(unreal.K2Node_FunctionEntry,unreal.K2Node_FunctionResult))]
        unreal.BlueprintGraphEditor.get_graph_editor(g).remove_nodes([n for n in B.find_nodes(g) if n not in keep])
    remove_variables(bp,['Money']);parent(bp,unreal.AnomalyWalletComponent.static_class())
    e=h.entry_node(add);n=native(add,'AnomalyWalletComponent','NativeAddMoney')
    wire(e,'then',n,'execute');wire(e,'Amount',n,'Amount')
    getter=native(get,'AnomalyWalletComponent','NativeGetMoney')
    ret=next(n for n in B.find_nodes(get) if isinstance(n,unreal.K2Node_FunctionResult))
    wire(getter,'ReturnValue',ret,'MoneyValue')
    reset_call=native(reset,'AnomalyWalletComponent','NativeResetMoney')
    wire(h.entry_node(reset),'then',reset_call,'execute')
    forward(bp,'PresentMoneyChanged','OnMoneyChanged',['NewMoney','Delta'])
    ASSETS.set_metadata_tag(bp,'CppMigrationVersion','1');compile_save(bp)


def box():
    bp=load(BOX)
    if ASSETS.get_metadata_tag(bp,'CppMigrationVersion')=='1': return
    g=unreal.BlueprintEditorLibrary.find_event_graph(bp)
    interact=next(n for n in B.find_nodes(g) if isinstance(n,unreal.K2Node_Event) and 'interact' in h.norm(n.get_node_title()))
    editor=unreal.BlueprintGraphEditor.get_graph_editor(g)
    editor.remove_nodes([n for n in B.find_nodes(g) if n!=interact])
    for fn in ('T11InitializeDefinition','T11LoadDefinition','T11ValidateDefinition','T11RollOutcome','T11RollReward'):
        B.remove_function_graph(bp,fn)
    old=json.loads((OUT/'pre_migration_assets.json').read_text(encoding='utf-8'))[BOX]['defaults']
    keep={'ForcedOutcome','OnBoxOpened','OnOutcomeResolved'}
    remove_variables(bp,[str(n) for n in B.list_variables(bp) if str(n) not in keep])
    parent(bp,unreal.AnomalyBoxActor.static_class())
    n=native(g,'AnomalyBoxActor','NativeInteract')
    wire(interact,'then',n,'execute');wire(interact,'Interactor',n,'Interactor')
    forced=editor.add_get_member_variable_node('ForcedOutcome')
    conv=editor.add_call_function_node('/Script/Engine.KismetMathLibrary:Conv_ByteToInt')
    wire(forced,'ForcedOutcome',conv,'InByte');wire(conv,'ReturnValue',n,'DebugOutcomeIndex')
    forward(bp,'PresentBoxOpened','OnBoxOpened',['Box'])
    outcome_forward(bp,'PresentOutcome','OnOutcomeResolved')
    B.compile_blueprint(bp)
    cdo=unreal.get_default_object(bp.generated_class())
    for key in ('RevealDelay','bDebugLogging','bForceOutcome','bUseFixedSeeds','ConfigurationSeed','OutcomeSeed','TrashAmount'):
        cdo.set_editor_property(key,old[key])
    for key in ('HighValueClass','TrashClass','ThreatClass'):
        cdo.set_editor_property(key,unreal.load_class(None,old[key]['object']))
    cdo.set_editor_property('OpeningAnimation',load('/Game/AnimatedWoodenCrateV1/Animations/AS_WoodenCrateOpen'))
    cdo.set_editor_property('OpeningSound',load('/Game/AnimatedWoodenCrateV1/Audio/SC_WoodenCrateOpen'))
    cdo.set_editor_property('Definitions',{r['Name']:load('/Game/Prototype/Data/Boxes/DA_Box_'+r['Name']) for r in ROWS})
    cdo.set_editor_property('DefinitionID',unreal.Name('None'))
    ASSETS.set_metadata_tag(bp,'CppMigrationVersion','1');compile_save(bp)


def spider():
    bp=load(SPIDER)
    if ASSETS.get_metadata_tag(bp,'CppMigrationVersion')=='1': return
    g=unreal.BlueprintEditorLibrary.find_event_graph(bp)
    # Retain only the T10 Tick execution/data subgraph. All other gameplay moves to C++.
    nodes=list(B.find_nodes(g));tick=next(n for n in nodes if isinstance(n,unreal.K2Node_Event) and 'tick' in h.norm(n.get_node_title()))
    retained={tick};queue=[tick]
    while queue:
        current=queue.pop()
        for p in h.input_pins(current)+h.output_pins(current):
            for q in p.list_connected_pins():
                other=q.get_owning_node()
                if other not in retained: retained.add(other);queue.append(other)
    unreal.BlueprintGraphEditor.get_graph_editor(g).remove_nodes([n for n in nodes if n not in retained])
    B.remove_function_graph(bp,'ResolveThreat')
    native_vars=['MoveSpeed','AcceptanceRadius','bAutoResolveThreat','AutoResolveDelay','bDebugLogging',
                 'bResolved','bAttackTriggered','bMoveRetryUsed','TargetPlayer']
    remove_variables(bp,native_vars);parent(bp,unreal.AnomalyThreatCharacter.static_class())
    forward(bp,'PresentThreatResolved','OnThreatResolved',['Spider'])
    forward(bp,'PresentPlayerAttacked','OnPlayerAttacked',['Spider'])
    ASSETS.set_metadata_tag(bp,'CppMigrationVersion','1');compile_save(bp)


def spawner():
    bp=load(SPAWNER)
    if ASSETS.get_metadata_tag(bp,'CppMigrationVersion')=='1': return
    clear_graph(unreal.BlueprintEditorLibrary.find_event_graph(bp))
    dispatchers=set(str(n) for n in unreal.BlueprintEditorLibrary.list_event_dispatchers(bp))
    for g in list(B.list_graphs(bp)):
        if g.get_name() not in dispatchers|{'EventGraph','UserConstructionScript'}:
            B.remove_function_graph(bp,g.get_name())
    remove_variables(bp,[str(n) for n in B.list_variables(bp) if str(n) not in dispatchers|{'RoundState','CurrentOutcome'}])
    parent(bp,unreal.AnomalyRoundCoordinator.static_class())
    forward(bp,'PresentThreatCount','OnThreatCountChanged',['Count','Maximum'])
    forward(bp,'PresentRoundAttack','OnAttackMessage',[])
    forward(bp,'PresentRunEnded','OnRunEnded',['bError'])
    outcome_forward(bp,'PresentRoundOutcome','OnOutcomeMessage')
    g=unreal.BlueprintEditorLibrary.find_event_graph(bp)
    e=event(bp,'PresentRoundState')
    editor=unreal.BlueprintGraphEditor.get_graph_editor(g)
    prev,prev_pin=e,'then'
    for i in range(4):
        eq=editor.add_call_function_node('/Script/Engine.KismetMathLibrary:EqualEqual_IntInt')
        wire(e,'StateIndex',eq,'A');t.val(eq,'B',i)
        branch=t.branch(g,prev,prev_pin,condition=(eq,'ReturnValue'))
        setter=editor.add_set_member_variable_node('RoundState')
        wire(branch,'then',setter,'execute');t.val(setter,'RoundState','NewEnumerator'+str(i))
        prev,prev_pin=branch,'else'
    B.compile_blueprint(bp)
    cdo=unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property('BoxClass',load(BOX).generated_class())
    ASSETS.set_metadata_tag(bp,'CppMigrationVersion','1');compile_save(bp)


def gameplay():
    configure_data();wallet();spider();box();spawner()
    for path in (h.CHARACTER_PATH,h.HUD_PATH,h.INTERACTION_PATH):
        bp=load(path);B.compile_blueprint(bp,warnings_as_errors=True)
        REPORT['checks'].append(path+' compiles without saving')


try:
    phase=RUN['asset_phase']
    journal(RUN,'asset_phase_started',phase=phase)
    if phase=='export':export()
    elif phase=='definition':definition()
    elif phase=='gameplay':gameplay()
    else:raise ValueError(phase)
    REPORT['status']='PASS'
except Exception:
    REPORT['status']='FAIL';REPORT['errors'].append(traceback.format_exc())
    unreal.log_error('[MIGRATION] FAIL '+REPORT['errors'][-1])
finally:
    write(OUT/('assets_'+RUN['asset_phase']+'.json'),REPORT)
    journal(RUN,'asset_phase_finished',phase=RUN['asset_phase'],status=REPORT['status'],modified=REPORT['modified_assets'],errors=REPORT['errors'])
    unreal.log('[MIGRATION] '+RUN['asset_phase']+' '+REPORT['status'])
