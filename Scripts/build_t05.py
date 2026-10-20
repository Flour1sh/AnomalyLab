"""Build T05 using in-process Unreal Python. Never starts MCP or PIE.

Run with RUN_T05.ps1. Only BP_Spider and BP_AnomalyBox are saved.
Existing box reward paths and all First Person/HUD assets are preserved.
"""
import sys
import shutil
from pathlib import Path
from datetime import datetime
import unreal

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'Scripts'))
import build_t04 as h
from editor_toolset.toolsets.blueprint import BlueprintTools as B
from editor_toolset.toolsets.actor import ActorTools as A
from editor_toolset.toolsets.blueprint import _BlueprintCache

SPIDER = '/Game/Anomalies/Creatures/BP_Spider'
MESH = '/Game/SciFiWorld/Meshes/SM_CreatureAlien06-Pose2'
TAG = 'T05_GENERATED'
h.TAG = TAG
h.PREFIX = '[T05]'
DEFAULTS = dict(MoveSpeed=350.0, AcceptanceRadius=80.0, bAttackTriggered=False,
                bResolved=False, bAutoResolveThreat=True, AutoResolveDelay=3.0,
                bDebugLogging=True, bMoveRetryUsed=False)

def log(s):
    unreal.log('[T05] ' + s)

def node(g, name, x=0, y=0):
    if name=='IsValid':
        return unreal.BlueprintGraphEditor.get_graph_editor(g).add_call_function_node('/Script/Engine.KismetSystemLibrary:IsValid')
    if name=='GetWorldTransform':
        return unreal.BlueprintGraphEditor.get_graph_editor(g).add_call_function_node('/Script/Engine.SceneComponent:K2_GetComponentToWorld')
    # Exact terminal matches avoid selecting unrelated similarly named methods.
    found = list(B.find_node_types(g, name))
    matches = [v for v in found if h.norm(str(v).split('|')[-1]) == h.norm(name)]
    if len(matches) != 1:
        raise RuntimeError(f'Expected one {name}: {matches}; candidates={found}')
    return h._tag(B.create_node(g, matches[0], unreal.IntPoint(x,y)))

def wire(a, ap, b, bp):
    if ap == 'Completed': ap = 'then'
    h.connect(a, [ap], b, [bp])

def val(n, p, v):
    h.set_default(n, [p], str(v).lower() if isinstance(v,bool) else v)

def getter(g, name):
    n=unreal.BlueprintGraphEditor.get_graph_editor(g).add_get_member_variable_node(name)
    assert n, name
    return n

def setter(g, name, value):
    n = unreal.BlueprintGraphEditor.get_graph_editor(g).add_set_member_variable_node(name)
    val(n,name,value)
    return n

def branch(g, source, source_pin='then', condition=None, variable=None):
    n=h._tag(B.create_node(g,'工具|流程控制|分支',unreal.IntPoint(0,0)))
    wire(source,source_pin,n,'execute')
    if variable:
        v=getter(g,variable); wire(v,variable,n,'Condition')
    elif condition:
        wire(condition[0],condition[1],n,'Condition')
    return n

def valid_branch(g, source, source_pin, obj, obj_pin):
    v=node(g,'IsValid')
    # This engine's stock library uses Object, rather than InputObject.
    h.connect(obj,[obj_pin],v,['Object','InputObject'])
    return branch(g,source,source_pin,(v,'ReturnValue'))

def printer(g, text, screen=False):
    n=node(g,'PrintString')
    val(n,'InString',text);val(n,'bPrintToScreen',screen);val(n,'bPrintToLog',True)
    if screen:
        val(n,'TextColor','(R=1.0,G=0.08,B=0.05,A=1.0)')
        val(n,'Duration',1.75)
    return n

def print_after(g, source, pin, text, screen=False):
    n=printer(g,text,screen);wire(source,pin,n,'execute');return n

def dispatch(g, name):
    n=node(g,'Call'+name)
    val(n,'Spider','self')
    return n

def delay(g, source, pin, seconds):
    n=node(g,'Delay');val(n,'Duration',seconds);wire(source,pin,n,'execute');return n

def call(g, name, source, pin='then'):
    n=node(g,name);wire(source,pin,n,'execute');return n

def compile_bp(bp, save=False):
    B.compile_blueprint(bp,warnings_as_errors=True)
    _BlueprintCache.invalidate(bp)
    for g in B.list_graphs(bp):
        assert not unreal.BlueprintGraphEditor.get_graph_editor(g).list_nodes_with_errors(), g.get_name()
    if save:
        assert h.ASSETS.save_loaded_asset(bp,only_if_is_dirty=False)

def components(bp):
    return A.get_components(unreal.get_default_object(bp.generated_class()))

def build_spider():
    bp=h.load(SPIDER) if h.ASSETS.does_asset_exist(SPIDER) else B.create('/Game/Anomalies/Creatures','BP_Spider',unreal.Character.static_class())
    log('Schema graphs: '+str([v.get_name() for v in B.list_graphs(bp)]))
    log('Schema dispatchers: '+str(list(unreal.BlueprintEditorLibrary.list_event_dispatchers(bp))))
    if h.ASSETS.get_metadata_tag(bp,'T05BuildVersion') in ('1','2'):
        compile_bp(bp)
        return bp
    # Only nodes owned by this generator are replaceable.
    g=unreal.BlueprintEditorLibrary.find_event_graph(bp)
    editor=unreal.BlueprintGraphEditor.get_graph_editor(g)
    existing=list(editor.list_all_nodes())
    assert len(existing)<=3, 'Existing unrecognized Spider graph; refusing to replace user work'
    preparing=h.ASSETS.get_metadata_tag(bp,'T05Schema')!='3'
    if preparing: editor.remove_nodes(existing)
    if preparing:
        for name,value in DEFAULTS.items():
            t=unreal.BlueprintEditorLibrary.get_basic_type_by_name('bool' if isinstance(value,bool) else 'real')
            h.ensure_variable(bp,name,t,name not in ('bResolved','bAttackTriggered','bMoveRetryUsed'))
            unreal.BlueprintEditorLibrary.change_member_variable_type(bp,name,t)
        h.ensure_variable(bp,'TargetPlayer',unreal.BlueprintEditorLibrary.get_object_reference_type(unreal.Character.static_class()),False)
        for name in ('OnThreatResolved','OnPlayerAttacked'):
            if name not in {str(n) for n in unreal.BlueprintEditorLibrary.list_event_dispatchers(bp)}:
                h.ensure_dispatcher(bp,name,[('object','Spider',unreal.Actor.static_class())])
    resolve=next((v for v in B.list_graphs(bp) if v.get_name().startswith('ResolveThreat')),None)
    if resolve is None: resolve=B.add_function_graph(bp,'ResolveThreat')
    if resolve.get_name()!='ResolveThreat': unreal.BlueprintEditorLibrary.rename_graph(resolve,'ResolveThreat')
    begin=h._tag(B.add_event(bp,'ReceiveBeginPlay'))
    chase=h._tag(B.add_event(bp,'StartChase'))
    overlap=h._tag(B.add_event(bp,'ReceiveActorBeginOverlap'))
    if preparing:
        h.ASSETS.set_metadata_tag(bp,'T05Schema','3')
        compile_bp(bp,True)
        log('SCHEMA PASS - restart Python batch to reload Blueprint schema')
        return None
    log('Threat node candidates: '+str(list(B.find_node_types(resolve,'Threat'))))

    # At most one resolution; set guard before notifying listeners.
    entry=h.entry_node(resolve)
    guard=branch(resolve,entry,variable='bResolved')
    print_after(resolve,guard,'then','[Threat] WARNING Duplicate ResolveThreat ignored')
    resolved=setter(resolve,'bResolved',True);wire(guard,'else',resolved,'execute')
    movement=getter(resolve,'CharacterMovement')
    stop=node(resolve,'DisableMovement');wire(movement,'CharacterMovement',stop,'self')
    wire(resolved,'then',stop,'execute')
    msg=print_after(resolve,stop,'then','[Threat] Resolved')
    notify=dispatch(resolve,'OnThreatResolved');wire(msg,'then',notify,'execute')

    # Independent auto resolution starts before movement; failures cannot cancel it.
    seq=h._tag(B.create_node(g,'工具|流程控制|序列',unreal.IntPoint(0,0)))
    wire(begin,'then',seq,'execute')
    auto=branch(g,seq,'then0',variable='bAutoResolveThreat')
    timer=node(g,'Delay');wire(auto,'then',timer,'execute')
    duration=getter(g,'AutoResolveDelay');wire(duration,'AutoResolveDelay',timer,'Duration')
    call(g,'ResolveThreat',timer,'Completed')
    movement=getter(g,'CharacterMovement')
    speed=editor.add_set_member_variable_node('MaxWalkSpeed','/Script/Engine.CharacterMovementComponent')
    wire(movement,'CharacterMovement',speed,'self')
    speed_value=getter(g,'MoveSpeed');wire(speed_value,'MoveSpeed',speed,'MaxWalkSpeed')
    wire(seq,'then1',speed,'execute');call(g,'StartChase',speed)

    # Poll again after successful arrival so the actor follows a moving player.
    guard=branch(g,chase,variable='bResolved')
    player=node(g,'GetPlayerCharacter')
    check=valid_branch(g,guard,'else',player,'ReturnValue')
    print_after(g,check,'else','[Threat] ERROR Player missing; auto-resolution remains active')
    cache=editor.add_set_member_variable_node('TargetPlayer')
    wire(check,'then',cache,'execute');wire(player,'ReturnValue',cache,'TargetPlayer')
    move=node(g,'AIMoveTo')
    wire(cache,'then',move,'execute')
    # Object-reference pins do not preserve the literal string "self". Use an
    # actual Self node so the movement proxy receives this Character.
    self_ref=h._tag(B.create_node(g,'变量|获得一个对自身的引用',unreal.IntPoint(1100,1760)))
    wire(self_ref,'self',move,'Pawn')
    wire(player,'ReturnValue',move,'TargetActor')
    acceptance=getter(g,'AcceptanceRadius');wire(acceptance,'AcceptanceRadius',move,'AcceptanceRadius')
    val(move,'bStopOnOverlap',False)
    again=delay(g,move,'OnSuccess',0.15);call(g,'StartChase',again,'Completed')
    active=branch(g,move,'OnFail',variable='bResolved')
    retry=branch(g,active,'else',variable='bMoveRetryUsed')
    print_after(g,retry,'then','[Threat] WARNING MoveTo failed twice; waiting for auto-resolution')
    used=setter(g,'bMoveRetryUsed',True);wire(retry,'else',used,'execute')
    warning=print_after(g,used,'then','[Threat] WARNING MoveTo failed; retry once in 0.5s')
    retry_wait=delay(g,warning,'then',0.5);call(g,'StartChase',retry_wait,'Completed')

    # Actor overlap is generated by the pawn-overlap capsule or AttackOverlap sphere.
    # The sphere accounts for MoveTo's goal radius while preserving AcceptanceRadius=80.
    active=branch(g,overlap,variable='bResolved')
    once=branch(g,active,'else',variable='bAttackTriggered')
    player=node(g,'GetPlayerCharacter')
    check=valid_branch(g,once,'else',player,'ReturnValue')
    equal=editor.add_call_function_node('/Script/Engine.KismetMathLibrary:EqualEqual_ObjectObject')
    wire(overlap,'OtherActor',equal,'A');wire(player,'ReturnValue',equal,'B')
    match=branch(g,check,'then',(equal,'ReturnValue'))
    attack=setter(g,'bAttackTriggered',True);wire(match,'then',attack,'execute')
    msg=print_after(g,attack,'then','[Threat] SPIDER ATTACKED',True)
    notify=dispatch(g,'OnPlayerAttacked');wire(msg,'then',notify,'execute')
    compile_bp(bp)

    if not any('AlienVisual' in c.get_name() for c in components(bp)):
        A.add_component(bp,unreal.StaticMeshComponent.static_class(),'AlienVisual')
    if not any('AttackOverlap' in c.get_name() for c in components(bp)):
        A.add_component(bp,unreal.SphereComponent.static_class(),'AttackOverlap')
    compile_bp(bp)
    cdo=unreal.get_default_object(bp.generated_class())
    for name,value in DEFAULTS.items(): cdo.set_editor_property(name,value)
    cdo.set_editor_property('auto_possess_ai',unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
    cdo.set_editor_property('ai_controller_class',unreal.AIController.static_class())
    cdo.set_editor_property('use_controller_rotation_yaw',False)
    cdo.set_editor_property('spawn_collision_handling_method',unreal.SpawnActorCollisionHandlingMethod.ADJUST_IF_POSSIBLE_BUT_ALWAYS_SPAWN)
    capsule=cdo.get_editor_property('capsule_component')
    capsule.set_capsule_size(34,45,False)
    capsule.set_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN,unreal.CollisionResponseType.ECR_OVERLAP)
    capsule.set_editor_property('generate_overlap_events',True)
    capsule.set_editor_property('can_ever_affect_navigation',False)
    movement=cdo.get_editor_property('character_movement')
    movement.set_editor_property('max_walk_speed',350.0)
    movement.set_editor_property('orient_rotation_to_movement',True)
    movement.set_editor_property('rotation_rate',unreal.Rotator(0,540,0))
    movement.set_editor_property('enable_physics_interaction',False)
    mesh=h.load(MESH);bounds=mesh.get_bounds();scale=90.0/(bounds.box_extent.z*2)
    visual=next(c for c in components(bp) if 'AlienVisual' in c.get_name())
    visual.set_static_mesh(mesh);visual.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    visual.set_editor_property('generate_overlap_events',False)
    visual.set_editor_property('can_ever_affect_navigation',False)
    visual.set_editor_property('relative_scale3d',unreal.Vector(scale,scale,scale))
    visual.set_editor_property('relative_location',unreal.Vector(-bounds.origin.x*scale,-bounds.origin.y*scale,-45-(bounds.origin.z-bounds.box_extent.z)*scale))
    sensor=next(c for c in components(bp) if 'AttackOverlap' in c.get_name())
    sensor.set_sphere_radius(80,False)
    sensor.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
    sensor.set_collision_object_type(unreal.CollisionChannel.ECC_WORLD_DYNAMIC)
    sensor.set_collision_response_to_all_channels(unreal.CollisionResponseType.ECR_IGNORE)
    sensor.set_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN,unreal.CollisionResponseType.ECR_OVERLAP)
    sensor.set_editor_property('generate_overlap_events',True)
    sensor.set_editor_property('can_ever_affect_navigation',False)
    for graph in (g,resolve): B.arrange_nodes(B.find_nodes(graph))
    h.ASSETS.set_metadata_tag(bp,'T05BuildVersion','2')
    compile_bp(bp,True)
    log('BP_Spider compiled and saved')
    return bp

def patch_box(spider):
    bp=h.load(h.BOX_PATH)
    g=unreal.BlueprintEditorLibrary.find_event_graph(bp)
    # Rebuilds leave a previously integrated box intact.
    integrated=h.ASSETS.get_metadata_tag(bp,'T05BuildVersion') in ('1','2')
    h.ensure_variable(bp,'ThreatClass',unreal.BlueprintEditorLibrary.get_class_reference_type(unreal.Actor.static_class()),True)
    compile_bp(bp)
    if not integrated:
        tails=[]
        for n in B.find_nodes(g):
            p=h.find_pin(n,'in',['InString'],False)
            if p and str(p.get_pin_value())=='[Box] Outcome=Threat': tails.append(n)
        assert len(tails)==2, f'Expected forced/random Threat tails, found {len(tails)}'
        for printer_node in tails:
            original=h.find_pin(printer_node,'out',['then']).list_connected_pins()[0]
            resolved=original.get_owning_node()
            notify=h.find_pin(resolved,'out',['then']).list_connected_pins()[0].get_owning_node()
            B.break_pins(B._pin_to_id(h.find_pin(printer_node,'out',['then'])),B._pin_to_id(original))
            point=getter(g,'CreatureSpawnPoint')
            transform=node(g,'GetWorldTransform');wire(point,'CreatureSpawnPoint',transform,'self')
            spawn=h.create(g,['SpawnActor','生成Actor'],0,0,input_words=('Class','SpawnTransform'),output_words=('ReturnValue',))
            cls=getter(g,'ThreatClass');wire(cls,'ThreatClass',spawn,'Class')
            wire(transform,'ReturnValue',spawn,'SpawnTransform');wire(printer_node,'then',spawn,'execute')
            val(spawn,'CollisionHandlingOverride','AdjustIfPossibleButAlwaysSpawn')
            check=valid_branch(g,spawn,'then',spawn,'ReturnValue')
            ok=print_after(g,check,'then','[Box] Threat Actor spawn succeeded')
            bad=print_after(g,check,'else','[Box] ERROR Threat Actor spawn failed')
            wire(ok,'then',resolved,'execute');wire(bad,'then',resolved,'execute')
            wire(spawn,'ReturnValue',notify,'SpawnedActor')
            valid=node(g,'IsValid');h.connect(spawn,['ReturnValue'],valid,['Object','InputObject'])
            wire(valid,'ReturnValue',notify,'bSpawnSucceeded')
    cdo=unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property('ThreatClass',spider.generated_class())
    # Spawn on clear floor beside the box so opening it does not begin inside the
    # attack overlap and the first path does not cross the pedestal.
    # Current placed box root is Z=50; capsule center Z=47 clears the lab floor.
    point=next(c for c in components(bp) if c.get_name().startswith('CreatureSpawnPoint'))
    point.set_editor_property('relative_location',unreal.Vector(250,-300,-3))
    h.ASSETS.set_metadata_tag(bp,'T05BuildVersion','2')
    compile_bp(bp,True)
    log('BP_AnomalyBox Threat paths compiled and saved; reward paths preserved')

def main():
    backup=ROOT/'Saved/T05'/('Backup_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup.mkdir(parents=True)
    for asset in (SPIDER,h.BOX_PATH):
        relative=Path(asset.replace('/Game/','')+'.uasset')
        source=ROOT/'Content'/relative
        if source.exists():
            dest=backup/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    log('Building assets; backup: '+str(backup))
    spider=build_spider()
    if spider is None: return
    patch_box(spider)
    log('BUILD PASS - assets saved; runtime acceptance NOT RUN')

if __name__=='__main__': main()
