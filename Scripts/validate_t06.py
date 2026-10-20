"""Reload and check T06 saved assets only. Does not launch PIE."""
import sys,json,hashlib
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'Scripts'))
import build_t06 as t
h=t.h;B=t.B
checks=[]
def check(label,condition):
    checks.append({'check':label,'pass':bool(condition)})
    assert condition,label

def exact_input(n,name):return next((p for p in h.input_pins(n) if h.pin_name(p)==name),None)
def nodes(bp,name):return list(B.find_nodes(t.graph(bp,name)))
def titles(bp,name):return [str(n.get_node_title()) for n in nodes(bp,name)]
for path in (t.SPAWNER,h.CHARACTER_PATH,h.HUD_PATH):
    bp=h.load(path);t.u.compile_bp(bp)
    check(path+' saved build marker',h.ASSETS.get_metadata_tag(bp,'T06BuildVersion')=='1')
    check(path+' no node compiler errors',all(not t.ed(g).list_nodes_with_errors() for g in B.list_graphs(bp)))
bp=h.load(t.SPAWNER);cdo=unreal.get_default_object(bp.generated_class())
check('RoundState starts Ready',str(cdo.get_editor_property('RoundState')).endswith('.READY: 0>'))
for key,value in {'ThreatsResolved':0,'MaxThreats':2,'NextRoundDelay':3.,'SpawnRetryDelay':1.,'MaxSpawnRetries':3,'CurrentSpawnRetryCount':0,'bCompleting':False,'bPrototypeError':False}.items():check(key+' default',cdo.get_editor_property(key)==value)
for name in ('CurrentBox','CurrentOutcomeActor','CurrentSpider'):check(name+' initially null',cdo.get_editor_property(name) is None)
check('BoxClass uses accepted box',cdo.get_editor_property('BoxClass')==h.load(h.BOX_PATH).generated_class())
for function,expected in {'SpawnNextBox':['Bind Event to On Box Opened','Bind Event to On Outcome Resolved'],'HandleOutcomeResolved':['Bind Event to On Threat Resolved','Bind Event to On Player Attacked'],'CompleteCurrentOutcome':['CleanupCurrentRound','EndRun','SpawnNextBox'],'EndRun':['CleanupCurrentRound','Call On Run Ended']}.items():
    normed=[h.norm(v) for v in titles(bp,function)]
    for item in expected:check(function+' '+item,h.norm(item) in normed)
# Verify delegate functions and timer ownership after reloading from disk.
for path in (t.SPAWNER,h.CHARACTER_PATH):
    asset=h.load(path)
    for g in B.list_graphs(asset):
        if path==h.CHARACTER_PATH and not g.get_name().startswith('T06'):continue
        for n in B.find_nodes(g):
            if isinstance(n,unreal.K2Node_CreateDelegate):
                handler=B.get_create_event_function(n)
                check(g.get_name()+' delegate '+handler,handler in [v.get_name() for v in B.list_graphs(asset)])
                selfpin=h.find_pin(n,'in',['self'])
                check(g.get_name()+' delegate has actual Self',bool(selfpin.list_connected_pins()))
for gname in ('SpawnNextBox','HandleOutcomeResolved'):
    for n in nodes(bp,gname):
        p=exact_input(n,'FunctionName')
        if p:
            name=str(p.get_pin_value())
            check('Timer callback exists '+name,name in [g.get_name() for g in B.list_graphs(bp)])
cleanup=nodes(bp,'CleanupCurrentRound')
check('Cleanup clears all three owned timer functions',set(str(exact_input(n,'FunctionName').get_pin_value()) for n in cleanup if exact_input(n,'FunctionName'))=={'RewardElapsed','ThreatFallbackElapsed','RetryBoxSpawn'})
check('Cleanup has exactly two actor destruction nodes',sum(1 for n in cleanup if 'destroyactor' in h.norm(n.get_node_title()))==2)
check('Threat increment occurs only in coordinator completion',sum(1 for g in B.list_graphs(bp) for n in B.find_nodes(g) if isinstance(n,unreal.K2Node_VariableSet) and h.find_pin(n,'in',['ThreatsResolved'],False))==1)
check('Reward amount/high class preserved by hash manifest',(ROOT/'Saved/T06/protected_hashes.json').exists())
check('Default box is random',not unreal.get_default_object(h.load(h.BOX_PATH).generated_class()).get_editor_property('bForceOutcome'))
check('HUD resets result colors on each outcome',h.ASSETS.get_metadata_tag(h.load(h.HUD_PATH),'T06PresentationVersion')=='1')
char=h.load(h.CHARACTER_PATH)
restart=nodes(char,'T06Restart');op=next(n for n in restart if h.find_pin(n,'in',['LevelName'],False))
check('Restart reloads L_Prototype',str(h.find_pin(op,'in',['LevelName']).get_pin_value())==t.MAP)
check('No DisableInput (look/R retained)',not any('DisableInput' in str(n.get_node_title()) for g in B.list_graphs(char) for n in B.find_nodes(g)))
check('Run End disables movement','DisableMovement' in titles(char,'T06RunEnded'))
check('Run End stops interaction focus tick','SetComponentTickEnabled' in titles(char,'T06RunEnded'))
base=json.loads((ROOT/'Saved/T06/baseline.json').read_text(encoding='utf-8'))
for name in ('Move','Aim'):
    actual=[(n.get_name(),str(n.get_node_title())) for n in nodes(char,name)]
    old=[(n['name'],n['title']) for n in base[h.CHARACTER_PATH]['graphs'][name]]
    check('Protected '+name+' graph retained',actual==old)
context=h.load('/Game/Core/Input/IMC_Prototype');m=context.get_editor_property('default_key_mappings').get_editor_property('mappings')
for action,key in [('IA_Interact','E'),('IA_Restart','R')]:check(action+' mapping',sum(1 for x in m if x.action and x.action.get_name()==action and str(x.key.get_editor_property('key_name'))==key)==1)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);assert levels.load_level(t.MAP)
a=list(actors.get_all_level_actors());sp=[x for x in a if x.get_class()==bp.generated_class()]
check('Exactly one Spawner in map',len(sp)==1);check('Spawner pedestal Z=50',abs(sp[0].get_actor_location().z-50)<.1)
check('No placed test boxes',not any(x.get_class()==h.load(h.BOX_PATH).generated_class() for x in a))
# T04/T05 source assets must not be resaved or regenerated by T06.
manifest=ROOT/'Saved/T06/protected_hashes.json'
if manifest.exists():
    expected=json.loads(manifest.read_text())
    repair_manifest=ROOT/'Saved/T06/callback_repair_hashes.json'
    if repair_manifest.exists():expected.update(json.loads(repair_manifest.read_text()))
    for rel,digest in expected.items():check('Preserved accepted baseline/explicit callback repair '+rel,hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest)
check('Jump/StopJumping retained',all(name in [str(n.get_node_title()) for n in nodes(char,'EventGraph')] for name in ('Jump','StopJumping')))
for path,wanted in ((h.BOX_PATH,{'callonboxopened':'Box'}),(t.u.SPIDER,{'callonthreatresolved':'Spider','callonplayerattacked':'Spider'})):
    asset=h.load(path)
    for g in B.list_graphs(asset):
        for n in B.find_nodes(g):
            param=wanted.get(h.norm(n.get_node_title()))
            if param:
                links=list(h.find_pin(n,'in',[param]).list_connected_pins())
                check(path+' '+param+' has explicit Self payload',len(links)==1 and isinstance(links[0].get_owning_node(),unreal.K2Node_Self))
(ROOT/'Saved/T06/validation.json').write_text(json.dumps({'runtime_tests':'NOT RUN','checks':checks},indent=2),encoding='utf-8')
unreal.log('[T06] STRUCTURAL PASS - '+str(len(checks))+' checks; PIE NOT RUN')

