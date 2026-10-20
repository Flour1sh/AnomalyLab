"""T06 asset-only Python build. No MCP, PIE, screen control or C++.
Schema is saved in a first process; graph construction runs after reload.
"""
import sys, shutil, json
from pathlib import Path
from datetime import datetime
import unreal
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'Scripts'))
import build_t04 as h
import build_t05 as u
from editor_toolset.toolsets.blueprint import BlueprintTools as B
h.TAG='T06_GENERATED'; h.PREFIX='[T06]'
SPAWNER='/Game/Anomalies/Containers/BP_BoxSpawner'
RESTART='/Game/Core/Input/IA_Restart'
MAP='/Game/Prototype/Maps/L_Prototype'
STATE='/Game/Core/Types/EPrototypeRoundState'
ASSETS=h.ASSETS
def wire(a,ap,b,bp):
    if isinstance(a,unreal.K2Node_SwitchEnum):
        names=('Ready','Revealing','OutcomeActive','Ended') if 'EPrototypeRoundState' in str(a.get_node_title()) else ('HighValue','Trash','Threat')
        if ap in names:ap='NewEnumerator'+str(names.index(ap))
    h.connect(a,['then' if ap=='Completed' else ap],b,[bp])
u.wire=wire
val=u.val; get=u.getter; branch=u.branch; valid=u.valid_branch

def log(s): unreal.log('[T06] '+s)
def ed(g): return unreal.BlueprintGraphEditor.get_graph_editor(g)
def native(g,path): return h._tag(ed(g).add_call_function_node(path))
def fn(g,name): return u.node(g,name)
def selfnode(g): return h._tag(B.create_node(g,'变量|获得一个对自身的引用',unreal.IntPoint(0,0)))
def call(g,name,src,pin='then',target=None):
    n=fn(g,name);wire(src,pin,n,'execute')
    if target:wire(target[0],target[1],n,'self')
    return n

def setv(g,name,src,pin='then',value=None,data=None):
    n=ed(g).add_set_member_variable_node(name);wire(src,pin,n,'execute')
    if data: wire(data[0],data[1],n,name)
    elif value is not None: val(n,name,value)
    return n

def graph(bp,name): return next(g for g in B.list_graphs(bp) if g.get_name()==name)
def entry(bp,name):
    g=graph(bp,name);return g,h.entry_node(g)
def guard(g,src,condition,pin='then',message='[Round] WARNING Duplicate or stale callback ignored'):
    b=branch(g,src,pin,condition);u.print_after(g,b,'else',message);return b

def equal(g,a,b,kind='ObjectObject'):
    n=native(g,'/Script/Engine.KismetMathLibrary:EqualEqual_'+kind)
    for p,v in [('A',a),('B',b)]:
        if isinstance(v,tuple):wire(v[0],v[1],n,p)
        else:val(n,p,v)
    return n,'ReturnValue'

def state_guard(g,src,state,pin='then'):
    sw=h.create(g,['EPrototypeRoundState'],0,0,include=('switch','EPrototypeRoundState'))
    wire(src,pin,sw,'execute');v=get(g,'RoundState');wire(v,'RoundState',sw,'Selection')
    for s in ('Ready','Revealing','OutcomeActive','Ended'):
        if s!=state:u.print_after(g,sw,s,'[Round] WARNING Ignored callback in '+s)
    return sw,state

def state_set(g,src,state,pin='then'):
    n=call(g,'SetRoundState',src,pin);val(n,'NewState',{'Ready':'NewEnumerator0','Revealing':'NewEnumerator1','OutcomeActive':'NewEnumerator2','Ended':'NewEnumerator3'}[state]);return n

def timer(g,src,name,seconds,pin='then'):
    n=native(g,'/Script/Engine.KismetSystemLibrary:K2_SetTimer');wire(src,pin,n,'execute')
    wire(selfnode(g),'self',n,'Object');val(n,'FunctionName',name);val(n,'bLooping',False)
    if isinstance(seconds,str):wire(get(g,seconds),seconds,n,'Time')
    else:val(n,'Time',seconds)
    return n

def bind(g,src,target,dispatcher,handler,pin='then'):
    n=h.create(g,[dispatcher],0,0,include=('bind',h.norm(dispatcher)))
    wire(src,pin,n,'execute');wire(target[0],target[1],n,'self')
    ce=h.create(g,['CreateEvent','创建事件'],0,0,output_words=('OutputDelegate',))
    wire(selfnode(g),'self',ce,'self');wire(ce,'OutputDelegate',n,'Delegate')
    B.set_create_event_function(ce,handler)
    assert B.get_create_event_function(ce)==handler
    return n

def emit(g,src,name,params=None,pin='then'):
    n=call(g,'Call'+name,src,pin)
    for p,v in (params or {}).items():wire(v[0],v[1],n,p)
    return n

def make_schema(bp,name,params=()):
    g=B.add_function_graph(bp,name)
    if g.get_name()!=name:unreal.BlueprintEditorLibrary.rename_graph(g,name)
    for p,t in params:
        ed(g).add_graph_input_parameter(p,t)
    return g

def compile_save(bp):
    u.compile_bp(bp,True)

def schema():
    if ASSETS.does_asset_exist(SPAWNER):
        bp=h.load(SPAWNER)
        assert ASSETS.get_metadata_tag(bp,'T06Schema')=='1','Unrecognized existing Spawner'
        return False
    backup=ROOT/'Saved/T06'/('Backup_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    for path in (h.CHARACTER_PATH,h.HUD_PATH,'/Game/Core/Input/IMC_Prototype',MAP):
        rel=Path(path.replace('/Game/','')+('.umap' if path==MAP else '.uasset'))
        dst=backup/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'Content'/rel,dst)
    log('Baseline backup: '+str(backup))
    bp=B.create('/Game/Anomalies/Containers','BP_BoxSpawner',unreal.Actor.static_class())
    basic=unreal.BlueprintEditorLibrary.get_basic_type_by_name
    obj=unreal.BlueprintEditorLibrary.get_object_reference_type
    enum=h.enum_pin_type(h.load(STATE)); outcome=h.enum_pin_type(h.load(h.OUTCOME_PATH))
    variables={'CurrentBox':obj(h.load(h.BOX_PATH).generated_class()),'CurrentOutcomeActor':obj(unreal.Actor.static_class()),'CurrentSpider':obj(h.load(u.SPIDER).generated_class()),'RoundState':enum,'CurrentOutcome':outcome,'ThreatsResolved':basic('int'),'MaxThreats':basic('int'),'NextRoundDelay':basic('real'),'SpawnRetryDelay':basic('real'),'MaxSpawnRetries':basic('int'),'CurrentSpawnRetryCount':basic('int'),'bDebugLogging':basic('bool'),'bCompleting':basic('bool'),'bAttackNotified':basic('bool'),'bPrototypeError':basic('bool'),'BoxClass':unreal.BlueprintEditorLibrary.get_class_reference_type(unreal.Actor.static_class())}
    for n,t in variables.items():h.ensure_variable(bp,n,t,n in ('BoxClass','MaxThreats','NextRoundDelay','SpawnRetryDelay','MaxSpawnRetries','bDebugLogging'))
    specs={'SpawnInitialBox':(),'SpawnNextBox':(),'RetryBoxSpawn':(),'HandleBoxInteractionStarted':(('Box',obj(unreal.Actor.static_class())),),'HandleOutcomeResolved':(('Outcome',outcome),('SpawnedActor',obj(unreal.Actor.static_class())),('bSpawnSucceeded',basic('bool'))),'HandleThreatResolved':(('Spider',obj(unreal.Actor.static_class())),),'HandlePlayerAttacked':(('Spider',obj(unreal.Actor.static_class())),),'CompleteCurrentOutcome':(),'CleanupCurrentRound':(),'SetRoundState':(('NewState',enum),),'EndRun':(),'RewardElapsed':(),'ThreatFallbackElapsed':()}
    for n,p in specs.items():make_schema(bp,n,p)
    for n,ps in {'OnOutcomeMessage':[('enum','Outcome',outcome),('object','SpawnedActor',unreal.Actor.static_class()),('basic','bSpawnSucceeded','bool')],'OnThreatCountChanged':[('basic','Count','int'),('basic','Maximum','int')],'OnRunEnded':[('basic','bError','bool')],'OnAttackMessage':[]}.items():h.ensure_dispatcher(bp,n,ps)
    ASSETS.set_metadata_tag(bp,'T06Schema','1');compile_save(bp)
    cdo=unreal.get_default_object(bp.generated_class())
    for n,v in dict(ThreatsResolved=0,MaxThreats=2,NextRoundDelay=3.,SpawnRetryDelay=1.,MaxSpawnRetries=3,CurrentSpawnRetryCount=0,bDebugLogging=True,bCompleting=False,bAttackNotified=False,bPrototypeError=False,BoxClass=h.load(h.BOX_PATH).generated_class()).items():cdo.set_editor_property(n,v)
    compile_save(bp)
    hud=h.load(h.HUD_PATH)
    for n,ps in {'T06UpdateThreats':(('Count',basic('int')),('Maximum',basic('int'))),'T06ShowAttack':(),'T06ShowEnd':(('FinalMoney',basic('int')),('Count',basic('int')),('Maximum',basic('int')),('bError',basic('bool')))}.items():make_schema(hud,n,ps)
    tree=h.UMG.call_method('GetWidgets',(hud,));root=next(v.widget for v in tree.widgets if str(v.widget_name)=='RootCanvas')
    panel=h.umg_add(hud,unreal.TextBlock.static_class(),'RunEndText',root)
    panel.widget.set_text(unreal.Text(''));panel.widget.set_font_size(34);panel.widget.set_editor_property('justification',unreal.TextJustify.CENTER)
    panel.widget.set_color_and_opacity(h.slate_color(1,.9,.75));panel.widget.set_visibility(unreal.SlateVisibility.COLLAPSED)
    h.set_canvas_slot(panel.slot,(.5,.5,.5,.5),(0,30),(900,260),(.5,.5));h.UMG.call_method('ToggleWidgetAsVariable',(hud,panel.widget,True))
    h.ensure_variable(hud,'bT06Ended',basic('bool'));compile_save(hud)
    char=h.load(h.CHARACTER_PATH)
    h.ensure_variable(char,'T06Spawner',obj(bp.generated_class()));h.ensure_variable(char,'bT06Ended',basic('bool'))
    for n,ps in {'T06ConnectSpawner':(),'T06ThreatChanged':(('Count',basic('int')),('Maximum',basic('int'))),'T06Attack':(),'T06RunEnded':(('bError',basic('bool')),),'T06Restart':()}.items():make_schema(char,n,ps)
    compile_save(char)
    action=unreal.AssetToolsHelpers.get_asset_tools().create_asset('IA_Restart','/Game/Core/Input',unreal.InputAction,unreal.InputAction_Factory())
    action.set_editor_property('value_type',unreal.InputActionValueType.BOOLEAN);ASSETS.save_loaded_asset(action,False)
    context=h.load('/Game/Core/Input/IMC_Prototype');data=context.get_editor_property('default_key_mappings');mappings=list(data.get_editor_property('mappings'))
    key=unreal.Key();key.set_editor_property('key_name','R');mapping=unreal.EnhancedActionKeyMapping();mapping.set_editor_property('action',action);mapping.set_editor_property('key',key);mappings.append(mapping);data.set_editor_property('mappings',mappings);context.set_editor_property('default_key_mappings',data);ASSETS.save_loaded_asset(context,False)
    log('SCHEMA PASS - reload before graph generation');return True


def build_spawner():
    bp=h.load(SPAWNER)
    if ASSETS.get_metadata_tag(bp,'T06BuildVersion')=='1':return
    # Schema-only assets are safe to retry: no graph changes are saved until complete.
    g,e=entry(bp,'SetRoundState');n=setv(g,'RoundState',e,data=(e,'NewState'))
    sw=h.create(g,['EPrototypeRoundState'],0,0,include=('switch','EPrototypeRoundState'));wire(n,'then',sw,'execute');wire(e,'NewState',sw,'Selection')
    for s in ('Ready','Revealing','OutcomeActive','Ended'):u.print_after(g,sw,s,'[Round] State='+s)
    g=unreal.BlueprintEditorLibrary.find_event_graph(bp);begin=B.add_event(bp,'ReceiveBeginPlay');call(g,'SpawnInitialBox',begin)
    g,e=entry(bp,'SpawnInitialBox');n=setv(g,'CurrentSpawnRetryCount',e,value=0);call(g,'SpawnNextBox',n)
    g,e=entry(bp,'SpawnNextBox');sw,p=state_guard(g,e,'Ready');current=get(g,'CurrentBox');b=valid(g,sw,p,current,'CurrentBox');u.print_after(g,b,'then','[Round] WARNING Box already exists')
    n=h.create(g,['SpawnActor','生成Actor'],0,0,input_words=('Class','SpawnTransform'),output_words=('ReturnValue',));wire(b,'else',n,'execute');wire(get(g,'BoxClass'),'BoxClass',n,'Class');transform=native(g,'/Script/Engine.Actor:GetTransform');wire(transform,'ReturnValue',n,'SpawnTransform');val(n,'CollisionHandlingOverride','AlwaysSpawn')
    cast=h.dynamic_cast_to(g,h.load(h.BOX_PATH).generated_class(),0,0);wire(n,'then',cast,'execute');wire(n,'ReturnValue',cast,'Object');castpin=next(h.pin_name(p) for p in h.output_pins(cast) if h.norm(h.pin_name(p)).startswith('as'))
    cb=setv(g,'CurrentBox',cast,data=(cast,castpin));cb=setv(g,'CurrentSpawnRetryCount',cb,value=0);cb=setv(g,'bCompleting',cb,value=False);cb=setv(g,'bAttackNotified',cb,value=False)
    cb=bind(g,cb,(get(g,'CurrentBox'),'CurrentBox'),'OnBoxOpened','HandleBoxInteractionStarted');cb=bind(g,cb,(get(g,'CurrentBox'),'CurrentBox'),'OnOutcomeResolved','HandleOutcomeResolved');cb=state_set(g,cb,'Ready');u.print_after(g,cb,'then','[Round] Next Box Spawn succeeded')
    fail=u.print_after(g,cast,'CastFailed','[Round] ERROR Box spawn failed')
    cmp=native(g,'/Script/Engine.KismetMathLibrary:Less_IntInt');wire(get(g,'CurrentSpawnRetryCount'),'CurrentSpawnRetryCount',cmp,'A');wire(get(g,'MaxSpawnRetries'),'MaxSpawnRetries',cmp,'B');b=branch(g,fail,condition=(cmp,'ReturnValue'));timer(g,b,'RetryBoxSpawn','SpawnRetryDelay')
    err=setv(g,'bPrototypeError',b,'else',value=True);call(g,'EndRun',err)
    g,e=entry(bp,'RetryBoxSpawn');sw,p=state_guard(g,e,'Ready');add=native(g,'/Script/Engine.KismetMathLibrary:Add_IntInt');wire(get(g,'CurrentSpawnRetryCount'),'CurrentSpawnRetryCount',add,'A');val(add,'B',1);n=setv(g,'CurrentSpawnRetryCount',sw,p,data=(add,'ReturnValue'));call(g,'SpawnNextBox',n)
    g,e=entry(bp,'HandleBoxInteractionStarted');sw,p=state_guard(g,e,'Ready');b=valid(g,sw,p,e,'Box');b=guard(g,b,equal(g,(e,'Box'),(get(g,'CurrentBox'),'CurrentBox')));state_set(g,b,'Revealing')
    g,e=entry(bp,'HandleOutcomeResolved');sw,p=state_guard(g,e,'Revealing');b=valid(g,sw,p,get(g,'CurrentBox'),'CurrentBox');n=setv(g,'CurrentOutcomeActor',b,data=(e,'SpawnedActor'));n=setv(g,'CurrentOutcome',n,data=(e,'Outcome'));n=state_set(g,n,'OutcomeActive');n=emit(g,n,'OnOutcomeMessage',{p:(e,p) for p in ('Outcome','SpawnedActor','bSpawnSucceeded')})
    sw=h.create(g,['EAnomalyOutcome'],0,0,include=('switch','EAnomalyOutcome'));wire(n,'then',sw,'execute');wire(e,'Outcome',sw,'Selection')
    for s in ('HighValue','Trash'):timer(g,sw,'RewardElapsed','NextRoundDelay',s)
    b=branch(g,sw,'Threat',(e,'bSpawnSucceeded'));check=valid(g,b,'then',e,'SpawnedActor');cast=h.dynamic_cast_to(g,h.load(u.SPIDER).generated_class(),0,0);wire(check,'then',cast,'execute');wire(e,'SpawnedActor',cast,'Object');cp=next(h.pin_name(p) for p in h.output_pins(cast) if h.norm(h.pin_name(p)).startswith('as'))
    n=setv(g,'CurrentSpider',cast,data=(cast,cp));n=bind(g,n,(get(g,'CurrentSpider'),'CurrentSpider'),'OnThreatResolved','HandleThreatResolved');bind(g,n,(get(g,'CurrentSpider'),'CurrentSpider'),'OnPlayerAttacked','HandlePlayerAttacked')
    error=u.printer(g,'[Round] ERROR Threat spawn failed; fallback resolution in 3 seconds')
    for src,p in ((b,'else'),(check,'else'),(cast,'CastFailed')):wire(src,p,error,'execute')
    timer(g,error,'ThreatFallbackElapsed',3.0)
    for handler in ('HandleThreatResolved','HandlePlayerAttacked'):
        g,e=entry(bp,handler);sw,p=state_guard(g,e,'OutcomeActive');b=valid(g,sw,p,e,'Spider');b=guard(g,b,equal(g,(e,'Spider'),(get(g,'CurrentOutcomeActor'),'CurrentOutcomeActor')))
        if handler=='HandleThreatResolved':call(g,'CompleteCurrentOutcome',b)
        else:
            once=branch(g,b,variable='bAttackNotified');n=setv(g,'bAttackNotified',once,'else',value=True);n=u.print_after(g,n,'then','[Round] SPIDER ATTACKED');emit(g,n,'OnAttackMessage')
    for handler,wanted in [('RewardElapsed',('HighValue','Trash')),('ThreatFallbackElapsed',('Threat',))]:
        g,e=entry(bp,handler);sw,p=state_guard(g,e,'OutcomeActive');out=h.create(g,['EAnomalyOutcome'],0,0,include=('switch','EAnomalyOutcome'));wire(sw,p,out,'execute');wire(get(g,'CurrentOutcome'),'CurrentOutcome',out,'Selection')
        for name in wanted:call(g,'CompleteCurrentOutcome',out,name)
    g,e=entry(bp,'CompleteCurrentOutcome');sw,p=state_guard(g,e,'OutcomeActive');b=branch(g,sw,p,variable='bCompleting');n=setv(g,'bCompleting',b,'else',value=True)
    sw=h.create(g,['EAnomalyOutcome'],0,0,include=('switch','EAnomalyOutcome'));wire(n,'then',sw,'execute');wire(get(g,'CurrentOutcome'),'CurrentOutcome',sw,'Selection')
    cleanup=fn(g,'CleanupCurrentRound')
    for s in ('HighValue','Trash'):wire(sw,s,cleanup,'execute')
    add=native(g,'/Script/Engine.KismetMathLibrary:Add_IntInt');wire(get(g,'ThreatsResolved'),'ThreatsResolved',add,'A');val(add,'B',1);count=setv(g,'ThreatsResolved',sw,'Threat',data=(add,'ReturnValue'));count=u.print_after(g,count,'then','[Round] Threat resolved; incrementing count');count=emit(g,count,'OnThreatCountChanged',{'Count':(get(g,'ThreatsResolved'),'ThreatsResolved'),'Maximum':(get(g,'MaxThreats'),'MaxThreats')});wire(count,'then',cleanup,'execute')
    cmp=native(g,'/Script/Engine.KismetMathLibrary:GreaterEqual_IntInt');wire(get(g,'ThreatsResolved'),'ThreatsResolved',cmp,'A');wire(get(g,'MaxThreats'),'MaxThreats',cmp,'B');b=branch(g,cleanup,condition=(cmp,'ReturnValue'));call(g,'EndRun',b);ready=state_set(g,b,'Ready','else');call(g,'SpawnNextBox',ready)
    g,e=entry(bp,'CleanupCurrentRound');n=e
    for name in ('RewardElapsed','ThreatFallbackElapsed','RetryBoxSpawn'):
        c=native(g,'/Script/Engine.KismetSystemLibrary:K2_ClearTimer');wire(n,'then',c,'execute');wire(selfnode(g),'self',c,'Object');val(c,'FunctionName',name);n=c
    # Clear references before DestroyActor so destruction cannot re-enter resolution.
    for variable,delegates in [('CurrentSpider',('OnThreatResolved','OnPlayerAttacked')),('CurrentBox',('OnBoxOpened','OnOutcomeResolved'))]:
        v=get(g,variable);check=valid(g,n,'then',v,variable);last=check
        for d in delegates:
            un=h.create(g,[d],0,0,include=('unbindall',h.norm(d)));wire(last,'then',un,'execute');wire(v,variable,un,'self');last=un
        merge=setv(g,'CurrentSpider' if variable=='CurrentSpider' else 'bAttackNotified',last,value=None if variable=='CurrentSpider' else False);wire(check,'else',merge,'execute');n=merge
    for variable in ('CurrentOutcomeActor','CurrentBox'):
        v=get(g,variable);check=valid(g,n,'then',v,variable);destroy=native(g,'/Script/Engine.Actor:K2_DestroyActor');wire(check,'then',destroy,'execute');wire(v,variable,destroy,'self');clear=setv(g,variable,destroy);wire(check,'else',clear,'execute');n=clear
    u.print_after(g,n,'then','[Round] Cleanup complete')
    g,e=entry(bp,'EndRun');sw=h.create(g,['EPrototypeRoundState'],0,0,include=('switch','EPrototypeRoundState'));wire(e,'then',sw,'execute');wire(get(g,'RoundState'),'RoundState',sw,'Selection');n=fn(g,'SetRoundState');val(n,'NewState','NewEnumerator3')
    for s in ('Ready','Revealing','OutcomeActive'):wire(sw,s,n,'execute')
    n=call(g,'CleanupCurrentRound',n);n=u.print_after(g,n,'then','[Round] Run Ended');emit(g,n,'OnRunEnded',{'bError':(get(g,'bPrototypeError'),'bPrototypeError')})
    for g in B.list_graphs(bp):B.arrange_nodes(B.find_nodes(g))
    ASSETS.set_metadata_tag(bp,'T06BuildVersion','1');compile_save(bp);log('Spawner compiled and saved')


def text_value(g,parts):
    """Build localized integer text (with grouping) without property bindings."""
    previous=None
    for part in parts:
        if isinstance(part,tuple):
            cv=native(g,'/Script/Engine.KismetTextLibrary:Conv_IntToText');wire(part[0],part[1],cv,'Value');val(cv,'bUseGrouping',True)
            st=native(g,'/Script/Engine.KismetTextLibrary:Conv_TextToString');wire(cv,'ReturnValue',st,'InText');item=(st,'ReturnValue')
        else:item=part
        if previous is None:previous=item;continue
        add=native(g,'/Script/Engine.KismetStringLibrary:Concat_StrStr')
        for pin,v in [('A',previous),('B',item)]:
            if isinstance(v,tuple):wire(v[0],v[1],add,pin)
            else:val(add,pin,v)
        previous=(add,'ReturnValue')
    cv=native(g,'/Script/Engine.KismetTextLibrary:Conv_StringToText')
    if isinstance(previous,tuple):wire(previous[0],previous[1],cv,'InString')
    else:val(cv,'InString',previous)
    return cv,'ReturnValue'

def widget_text(g,src,widget,parts,pin='then'):
    n=native(g,'/Script/UMG.TextBlock:SetText');wire(src,pin,n,'execute');wire(get(g,widget),widget,n,'self');t=text_value(g,parts);wire(t[0],t[1],n,'InText');return n

def visibility(g,src,widget,visible,pin='then'):
    n=native(g,'/Script/UMG.Widget:SetVisibility');wire(src,pin,n,'execute');wire(get(g,widget),widget,n,'self');val(n,'InVisibility','SelfHitTestInvisible' if visible else 'Collapsed');return n

def hud_valid(g,src,pin='then'):
    v=get(g,'PrototypeHUD');b=valid(g,src,pin,v,'PrototypeHUD');u.print_after(g,b,'else','[HUD] WARNING Optional HUD unavailable');return b,v

def build_hud():
    bp=h.load(h.HUD_PATH)
    if ASSETS.get_metadata_tag(bp,'T06BuildVersion')=='1':return
    g,e=entry(bp,'T06UpdateThreats');widget_text(g,e,'ThreatText',['Threats: ',(e,'Count'),' / ',(e,'Maximum')])
    g,e=entry(bp,'T06ShowAttack');b=branch(g,e,variable='bT06Ended');n=widget_text(g,b,'ResultText',['SPIDER ATTACKED'],'else');color=native(g,'/Script/UMG.TextBlock:SetColorAndOpacity');wire(n,'then',color,'execute');wire(get(g,'ResultText'),'ResultText',color,'self');val(color,'InColorAndOpacity','(SpecifiedColor=(R=1.0,G=0.08,B=0.05,A=1.0),ColorUseRule=UseColor_Specified)');call(g,'AnimateResult',color)
    g,e=entry(bp,'T06ShowEnd');n=setv(g,'bT06Ended',e,value=True);n=visibility(g,n,'InteractionPrompt',False);n=visibility(g,n,'ResultText',False);n=visibility(g,n,'RunEndText',True);b=branch(g,n,condition=(e,'bError'))
    widget_text(g,b,'RunEndText',['PROTOTYPE ERROR\nPress R to Restart'])
    widget_text(g,b,'RunEndText',['RUN OVER\nFinal Money: $',(e,'FinalMoney'),'\nThreats: ',(e,'Count'),' / ',(e,'Maximum'),'\nPress R to Restart'],'else')
    # Ignore focus/outcome presentations after run end. Preserve existing animation.
    for name in ('UpdateFocus','ShowOutcome'):
        g=graph(bp,name);e=h.entry_node(g);p=h.find_pin(e,'out',['then']);old=list(p.list_connected_pins());assert len(old)==1
        dst=old[0];B.break_pins(B._pin_to_id(p),B._pin_to_id(dst));b=branch(g,e,variable='bT06Ended');h.find_pin(b,'out',['else']).try_create_connection(dst)
    ASSETS.set_metadata_tag(bp,'T06BuildVersion','1');compile_save(bp);log('HUD compiled and saved')

def build_character():
    bp=h.load(h.CHARACTER_PATH)
    if ASSETS.get_metadata_tag(bp,'T06BuildVersion')=='1':return
    g,e=entry(bp,'T06ConnectSpawner');n=native(g,'/Script/Engine.GameplayStatics:GetActorOfClass');wire(e,'then',n,'execute');val(n,'ActorClass',h.load(SPAWNER).generated_class().get_path_name());b=valid(g,n,'then',n,'ReturnValue');u.print_after(g,b,'else','[Round] ERROR Missing BP_BoxSpawner')
    # GetActorOfClass specializes its output from ActorClass.
    n=setv(g,'T06Spawner',b,data=(n,'ReturnValue'))
    for dispatcher,handler in [('OnOutcomeMessage','HandleOutcomeResolved'),('OnThreatCountChanged','T06ThreatChanged'),('OnAttackMessage','T06Attack'),('OnRunEnded','T06RunEnded')]:n=bind(g,n,(get(g,'T06Spawner'),'T06Spawner'),dispatcher,handler)
    n=call(g,'T06ThreatChanged',n);val(n,'Count',0);val(n,'Maximum',2)
    # Snapshot state handles the rare case where Spawner ended before player BeginPlay.
    st=ed(g).add_get_member_variable_node('RoundState',h.load(SPAWNER).generated_class().get_path_name());wire(get(g,'T06Spawner'),'T06Spawner',st,'self');sw=h.create(g,['EPrototypeRoundState'],0,0,include=('switch','EPrototypeRoundState'));wire(n,'then',sw,'execute');wire(st,'RoundState',sw,'Selection');end=call(g,'T06RunEnded',sw,'Ended');val(end,'bError',True)
    for handler,method,params in [('T06ThreatChanged','T06UpdateThreats',('Count','Maximum')),('T06Attack','T06ShowAttack',())]:
        g,e=entry(bp,handler);b,v=hud_valid(g,e);n=call(g,method,b,target=(v,'PrototypeHUD'))
        for p in params:wire(e,p,n,p)
    g,e=entry(bp,'T06RunEnded');b=branch(g,e,variable='bT06Ended');n=setv(g,'bT06Ended',b,'else',value=True);movement=get(g,'CharacterMovement');n=call(g,'DisableMovement',n,target=(movement,'CharacterMovement'))
    controller=native(g,'/Script/Engine.Pawn:GetController');check=valid(g,n,'then',controller,'ReturnValue');ignore=native(g,'/Script/Engine.Controller:SetIgnoreMoveInput');wire(check,'then',ignore,'execute');wire(controller,'ReturnValue',ignore,'self');val(ignore,'bNewMoveInput',True)
    interaction=get(g,'BPC_Interaction');tick=native(g,'/Script/Engine.ActorComponent:SetComponentTickEnabled');wire(ignore,'then',tick,'execute');wire(check,'else',tick,'execute');wire(interaction,'BPC_Interaction',tick,'self');val(tick,'bEnabled',False)
    b,v=hud_valid(g,tick)
    wallet=get(g,'BPC_Wallet');money=call(g,'GetMoney',b);wire(wallet,'BPC_Wallet',money,'self')
    n=call(g,'T06ShowEnd',money,target=(v,'PrototypeHUD'));wire(e,'bError',n,'bError');wire(money,'MoneyValue',n,'FinalMoney')
    for var,param in [('ThreatsResolved','Count'),('MaxThreats','Maximum')]:
        v=ed(g).add_get_member_variable_node(var,h.load(SPAWNER).generated_class().get_path_name());wire(get(g,'T06Spawner'),'T06Spawner',v,'self');wire(v,var,n,param)
    g,e=entry(bp,'T06Restart');v=get(g,'T06Spawner');b=valid(g,e,'then',v,'T06Spawner');st=ed(g).add_get_member_variable_node('RoundState',h.load(SPAWNER).generated_class().get_path_name());wire(v,'T06Spawner',st,'self');sw=h.create(g,['EPrototypeRoundState'],0,0,include=('switch','EPrototypeRoundState'));wire(b,'then',sw,'execute');wire(st,'RoundState',sw,'Selection');n=u.print_after(g,sw,'Ended','[Round] Restart L_Prototype');op=native(g,'/Script/Engine.GameplayStatics:OpenLevel');wire(n,'then',op,'execute');val(op,'LevelName',MAP)
    g=unreal.BlueprintEditorLibrary.find_event_graph(bp)
    # Replace only the previously inspected T04 single-box subscription tail.
    byname={n.get_name():n for n in B.find_nodes(g)}
    old=byname['K2Node_CallFunction_17'];assert str(h.find_pin(old,'in',['ActorClass']).get_pin_value()).startswith(h.BOX_PATH)
    upstream=h.find_pin(old,'in',['execute']).list_connected_pins()[0]
    ed(g).remove_nodes([byname[n] for n in ('K2Node_CallFunction_17','K2Node_CallFunction_18','K2Node_IfThenElse_1','K2Node_AddDelegate_3','K2Node_CreateDelegate_3','K2Node_CallFunction_19')])
    call(g,'T06ConnectSpawner',upstream.get_owning_node(),h.pin_name(upstream))
    # HUD creation failure must not prevent run-end subscriptions/gameplay.
    call(g,'T06ConnectSpawner',byname['K2Node_CallFunction_12'])
    interact=byname['K2Node_EnhancedInputAction_9'];p=h.find_pin(interact,'out',['Started']);dest=p.list_connected_pins()[0];B.break_pins(B._pin_to_id(p),B._pin_to_id(dest));b=branch(g,interact,'Started',variable='bT06Ended');assert h.find_pin(b,'out',['else']).try_create_connection(dest)
    restart=h.create(g,['IA_Restart'],0,0,include=('ia_restart',),exclude=('get','mapping'),output_words=('Started',));call(g,'T06Restart',restart,'Started')
    # Add validity checks to existing HUD forwarding functions, keeping their payloads.
    for name in ('HandleMoneyChanged_6','HandleFocusChanged_6','HandleOutcomeResolved'):
        fg=graph(bp,name);en=h.entry_node(fg);p=h.find_pin(en,'out',['then']);dst=p.list_connected_pins()[0];B.break_pins(B._pin_to_id(p),B._pin_to_id(dst));b,v=hud_valid(fg,en);assert h.find_pin(b,'out',['then']).try_create_connection(dst)
    for g in B.list_graphs(bp):
        if g.get_name().startswith('T06'):B.arrange_nodes(B.find_nodes(g))
    ASSETS.set_metadata_tag(bp,'T06BuildVersion','1');compile_save(bp);log('Player compiled and saved; Move/Aim/Jump graphs preserved')

def build_map():
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    assert levels.load_level(MAP)
    allactors=list(actors.get_all_level_actors());spawners=[a for a in allactors if a.get_class()==h.load(SPAWNER).generated_class()]
    boxes=[a for a in allactors if a.get_class()==h.load(h.BOX_PATH).generated_class()]
    if not spawners:
        assert len(boxes)==1,'Expected exactly the accepted pedestal test box'
        box=boxes[0];transform=box.get_actor_transform()
        spawned=actors.spawn_actor_from_class(h.load(SPAWNER).generated_class(),box.get_actor_location(),box.get_actor_rotation());assert spawned
        spawned.set_actor_transform(transform,False,False);spawned.set_actor_label('PROTOTYPE_BoxSpawner_T06')
    else:assert len(spawners)==1
    for box in boxes:assert actors.destroy_actor(box)
    assert levels.save_current_level();log('Map saved with one Spawner and no placed test box')

def finalize_details():
    hud=h.load(h.HUD_PATH)
    if ASSETS.get_metadata_tag(hud,'T06PresentationVersion')!='1':
        g=graph(hud,'ShowOutcome')
        sw=next(n for n in B.find_nodes(g) if isinstance(n,unreal.K2Node_SwitchEnum))
        for index,color in enumerate(((1.0,.72,.08),(.65,.65,.65),(1.0,.08,.05))):
            p=h.find_pin(sw,'out',['NewEnumerator'+str(index)]);dst=p.list_connected_pins()[0]
            B.break_pins(B._pin_to_id(p),B._pin_to_id(dst))
            n=native(g,'/Script/UMG.TextBlock:SetColorAndOpacity')
            wire(sw,'NewEnumerator'+str(index),n,'execute');wire(get(g,'ResultText'),'ResultText',n,'self')
            val(n,'InColorAndOpacity','(SpecifiedColor=(R=%s,G=%s,B=%s,A=1.0),ColorUseRule=UseColor_Specified)'%color)
            assert h.find_pin(n,'out',['then']).try_create_connection(dst)
        ASSETS.set_metadata_tag(hud,'T06PresentationVersion','1');compile_save(hud)
    bp=h.load(SPAWNER)
    if ASSETS.get_metadata_tag(bp,'T06LogVersion')!='1':
        g=graph(bp,'CompleteCurrentOutcome')
        printer=next(n for n in B.find_nodes(g) if h.find_pin(n,'in',['InString'],False) and str(h.find_pin(n,'in',['InString']).get_pin_value()).startswith('[Round] Threat resolved'))
        value=text_value(g,['[Round] Threat resolved; count=',(get(g,'ThreatsResolved'),'ThreatsResolved'),' / ',(get(g,'MaxThreats'),'MaxThreats')])
        cv=native(g,'/Script/Engine.KismetTextLibrary:Conv_TextToString');wire(value[0],value[1],cv,'InText');wire(cv,'ReturnValue',printer,'InString')
        g=graph(bp,'EndRun');e=h.entry_node(g);p=h.find_pin(e,'out',['then']);dst=p.list_connected_pins()[0];B.break_pins(B._pin_to_id(p),B._pin_to_id(dst))
        b=branch(g,e,variable='bPrototypeError');error=u.print_after(g,b,'then','[Round] ERROR Box retries exhausted; PROTOTYPE ERROR')
        assert h.find_pin(error,'out',['then']).try_create_connection(dst)
        assert h.find_pin(b,'out',['else']).try_create_connection(dst)
        ASSETS.set_metadata_tag(bp,'T06LogVersion','1');compile_save(bp)

def repair_callback_senders():
    # Object payloads do not inherit the implicit Self of the dispatcher target.
    # The T02/T05 literal "self" default was serialized as an empty object value.
    for path,dispatchers in ((h.BOX_PATH,{'CallOnBoxOpened':'Box'}),(u.SPIDER,{'CallOnThreatResolved':'Spider','CallOnPlayerAttacked':'Spider'})):
        bp=h.load(path);changed=False
        for g in B.list_graphs(bp):
            for n in list(B.find_nodes(g)):
                key=h.norm(n.get_node_title())
                param=next((v for k,v in dispatchers.items() if h.norm(k)==key),None)
                if not param:continue
                pin=h.find_pin(n,'in',[param])
                if not list(pin.list_connected_pins()):
                    wire(selfnode(g),'self',n,param);changed=True
        if changed:compile_save(bp)

if __name__=='__main__':
    import runpy
    runpy.run_path(str(ROOT/'Scripts/repair_t06_enum.py'))
    if not schema():
        repair_callback_senders();build_spawner();build_hud();build_character();finalize_details();build_map()
        log('BUILD PASS - assets generated; PIE/runtime acceptance NOT RUN')


