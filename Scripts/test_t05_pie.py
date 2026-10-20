"""T05 PIE-only harness, launched through the UE MCP console. Never saves assets.

Case selected in Saved/T05/case.json. Uses a fresh PIE world for each case.
Records properties, positions and game-time transitions on Slate ticks.
Does not access Blueprint delegate wrappers (unsafe in this UE build).
Event broadcast counts must be checked separately; transitions are not broadcasts.
"""
import builtins
import json
import traceback
from pathlib import Path
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
OUT=ROOT/'Saved/T05'
MODE=json.loads((OUT/'case.json').read_text(encoding='utf-8'))['case']
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world is not None, 'A fresh PIE world is required'
assert getattr(builtins,'T05_HANDLE',None) is None, 'Previous harness is still running'
box_cls=unreal.load_class(None,'/Game/Anomalies/Containers/BP_AnomalyBox.BP_AnomalyBox_C')
spider_cls=unreal.load_class(None,'/Game/Anomalies/Creatures/BP_Spider.BP_Spider_C')
box=unreal.GameplayStatics.get_all_actors_of_class(world,box_cls)[0]
player=unreal.GameplayStatics.get_player_character(world,0)
assert player is not None and not box.get_editor_property('bOpened')
player.set_actor_location(unreal.Vector(430,0,100),False,True)
start=unreal.GameplayStatics.get_time_seconds(world)
state={'case':MODE,'started_game_time':start,'events':[],'samples':[], 'errors':[],
       'done':False,'spawn_count':0,'attack_transitions':0,'resolve_transitions':0,
       'broadcast_counts_verified':False}
refs={'spider':None,'last_sample':-1,'moved_after_attack':False,'duplicate_resolve':False,'manual_resolve':False}
builtins.T05_STATE=state
builtins.T05_REFS=refs

def now(): return float(unreal.GameplayStatics.get_time_seconds(world))
def vec(v):return [round(float(v.x),3),round(float(v.y),3),round(float(v.z),3)]
def record(event,**extra):
    row={'event':event,'t':round(now()-start,4),**extra}
    state['events'].append(row)
    unreal.log('[T05PIE] '+json.dumps(row))

def finish():
    state['done']=True
    state['ended_game_time']=now()
    (OUT/('pie_'+MODE+'.json')).write_text(json.dumps(state,indent=2),encoding='utf-8')
    unreal.log('[T05PIE] CASE COMPLETE '+MODE+' '+json.dumps({k:state[k] for k in ('spawn_count','attack_transitions','resolve_transitions','errors')}))
    handle=getattr(builtins,'T05_HANDLE',None)
    if handle is not None: unreal.unregister_slate_post_tick_callback(handle)
    builtins.T05_HANDLE=None

def tick(dt):
    try:
        if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()!=world:
            state['errors'].append('PIE stopped before completion');finish();return
        elapsed=now()-start
        actors=unreal.GameplayStatics.get_all_actors_of_class(world,spider_cls)
        state['spawn_count']=max(state['spawn_count'],len(actors))
        if refs['spider'] is None and actors:
            refs['spider']=actors[0]
            record('spawn_first_observed',location=vec(actors[0].get_actor_location()),
                   age=float(actors[0].get_game_time_since_creation()),
                   controller=actors[0].get_controller().get_class().get_name() if actors[0].get_controller() else None)
        spider=refs['spider']
        if spider is not None:
            age=float(spider.get_game_time_since_creation())
            if spider.get_editor_property('bAttackTriggered') and not state['attack_transitions']:
                state['attack_transitions']=1
                record('attack_flag_observed',age=age)
            if spider.get_editor_property('bResolved') and not state['resolve_transitions']:
                state['resolve_transitions']=1
                record('resolved_flag_observed',age=age)
            if elapsed-refs['last_sample']>=0.05:
                refs['last_sample']=elapsed
                state['samples'].append({'t':round(elapsed,4),'age':round(age,4),'location':vec(spider.get_actor_location()),
                    'velocity':vec(spider.get_velocity()),'player':vec(player.get_actor_location()),
                    'yaw':float(spider.get_actor_rotation().yaw),'attack':bool(spider.get_editor_property('bAttackTriggered')),
                    'resolved':bool(spider.get_editor_property('bResolved')),'retry':bool(spider.get_editor_property('bMoveRetryUsed')),
                    'movement_mode':str(spider.get_editor_property('character_movement').get_editor_property('movement_mode'))})
            if MODE=='normal' and state['attack_transitions'] and not refs['moved_after_attack']:
                refs['moved_after_attack']=True
                player.set_actor_location(unreal.Vector(430,330,100),False,True)
                record('player_moved_after_attack',location=vec(player.get_actor_location()))
            if MODE=='normal' and 2.5<age<2.9 and not refs.get('reentered'):
                refs['reentered']=True
                loc=spider.get_actor_location()
                player.set_actor_location(unreal.Vector(loc.x+20,loc.y,100),False,True)
                record('player_reentered_overlap')
            if MODE=='manual' and age>3.4 and not refs['manual_resolve']:
                refs['manual_resolve']=True
                record('manual_before_resolve',resolved=bool(spider.get_editor_property('bResolved')))
                spider.call_method('ResolveThreat')
            if bool(spider.get_editor_property('bResolved')) and not refs['duplicate_resolve']:
                refs['duplicate_resolve']=True
                spider.call_method('ResolveThreat');spider.call_method('ResolveThreat')
                record('duplicate_resolve_calls',count=2,resolved=bool(spider.get_editor_property('bResolved')))
        if elapsed>6.0:finish()
    except Exception:
        error=traceback.format_exc();state['errors'].append(error);unreal.log_error('[T05PIE] '+error);finish()

if MODE=='manual':
    transform=unreal.Transform(location=unreal.Vector(120,0,47))
    spider=unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(world,spider_cls,transform,unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN)
    spider.set_editor_property('bAutoResolveThreat',False)
    unreal.GameplayStatics.finish_spawning_actor(spider,transform)
    refs['spider']=spider;state['spawn_count']=1
    record('manual_spawn',location=vec(spider.get_actor_location()))
else:
    box.set_editor_property('bForceOutcome',True)
    enum=type(box.get_editor_property('ForcedOutcome'))
    box.set_editor_property('ForcedOutcome',enum.THREAT)
    if MODE=='nav_failure':
        point=next(c for c in box.get_components_by_class(unreal.SceneComponent) if c.get_name()=='CreatureSpawnPoint')
        point.set_world_location(unreal.Vector(5000,5000,47),False,True)
    if MODE=='spawn_failure':box.set_editor_property('ThreatClass',None)
    record('interact_twice')
    box.call_method('Interact',(player,));box.call_method('Interact',(player,))
    if MODE=='missing_player':
        player.get_controller().un_possess()
        record('player_unpossessed')
builtins.T05_HANDLE=unreal.register_slate_post_tick_callback(tick)
unreal.log('[T05PIE] CASE START '+MODE)
