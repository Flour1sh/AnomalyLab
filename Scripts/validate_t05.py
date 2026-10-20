"""Read-only saved-asset T05 validation. Does not start gameplay or save assets."""
import sys
import json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'Scripts'))
import build_t05 as t

def main():
    b=t.B;h=t.h
    report={'runtime_acceptance':'NOT RUN - deferred by user','checks':[]}
    def check(ok, description):
        report['checks'].append({'check':description,'pass':bool(ok)})
        if not ok: raise AssertionError(description)
    spider=h.load(t.SPIDER);box=h.load(h.BOX_PATH)
    for bp in (spider,box):
        t.compile_bp(bp)
        check(h.ASSETS.get_metadata_tag(bp,'T05BuildVersion') in ('1','2'),bp.get_name()+' build marker and compile')
    cdo=unreal.get_default_object(spider.generated_class())
    check(unreal.MathLibrary.class_is_child_of(spider.generated_class(),unreal.Character.static_class()),'Character parent')
    for name,value in t.DEFAULTS.items():
        check(cdo.get_editor_property(name)==value,'Default '+name+'='+str(value))
    check(cdo.get_editor_property('auto_possess_ai')==unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED,'AI possession includes spawn')
    check(cdo.get_editor_property('ai_controller_class')==unreal.AIController.static_class(),'AIController configured')
    capsule=cdo.get_editor_property('capsule_component')
    check(capsule.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN)==unreal.CollisionResponseType.ECR_OVERLAP,'Capsule overlaps Pawn')
    move=cdo.get_editor_property('character_movement')
    check(move.get_editor_property('max_walk_speed')==350,'Movement speed 350')
    check(move.get_editor_property('orient_rotation_to_movement'),'Faces movement')
    check(not move.get_editor_property('enable_physics_interaction'),'No physics pushing')
    visual=next(c for c in t.components(spider) if 'AlienVisual' in c.get_name())
    check(visual.get_editor_property('static_mesh').get_path_name().split('.')[0]==t.MESH,'Selected Alien mesh')
    check(visual.get_collision_enabled()==unreal.CollisionEnabled.NO_COLLISION,'Visual has no collision')
    height=visual.get_editor_property('static_mesh').get_bounds().box_extent.z*2*visual.get_editor_property('relative_scale3d').z
    check(abs(height-90)<.01,'Visual height 90 cm')
    sensor=next(c for c in t.components(spider) if 'AttackOverlap' in c.get_name())
    check(abs(sensor.get_unscaled_sphere_radius()-80)<.01,'Attack overlap radius 80')
    check({'OnThreatResolved','OnPlayerAttacked'}.issubset({str(n) for n in unreal.BlueprintEditorLibrary.list_event_dispatchers(spider)}),'Stable dispatchers')
    graphs={g.get_name():g for g in b.list_graphs(spider)}
    check('ResolveThreat' in graphs,'ResolveThreat function')
    def infos(bp):
        return [b._get_node_info(n) for g in b.list_graphs(bp) for n in b.find_nodes(g)]
    sn=infos(spider);bn=infos(box)
    report['spider_node_count']=len(sn)
    move_nodes=[n for n in sn if str(n.type_id).endswith('|AIMoveTo')]
    check(len(move_nodes)==1,'One asynchronous AI MoveTo path')
    move_pins={p.name:p for p in move_nodes[0].input_pins}
    check(len(move_pins['Pawn'].connected_pins)==1,'AI MoveTo Pawn is connected to Self')
    check(sum(str(n.type_id).endswith('|CallOnThreatResolved') for n in sn)==1,'One resolution broadcast site')
    check(sum(str(n.type_id).endswith('|CallOnPlayerAttacked') for n in sn)==1,'One attack broadcast site')
    check(any(any(str(p.value)=='[Threat] SPIDER ATTACKED' for p in n.input_pins) for n in sn),'Attack feedback exists')
    check(any(any(p.name=='Duration' and abs(float(p.value or '-1')-.5)<.001 for p in n.input_pins) for n in sn if str(n.type_id).endswith('|Delay')),'0.5 second retry')
    box_default=unreal.get_default_object(box.generated_class())
    check(box_default.get_editor_property('ThreatClass')==spider.generated_class(),'Box ThreatClass references saved Spider')
    threat_calls=[]
    for n in bn:
        if not str(n.type_id).endswith('|CallOnOutcomeResolved'): continue
        pins={p.name:p for p in n.input_pins}
        if str(pins['Outcome'].value)=='NewEnumerator2':
            threat_calls.append(n)
            check(len(pins['SpawnedActor'].connected_pins)==1,'Threat dispatcher uses spawn return Actor')
            check(len(pins['bSpawnSucceeded'].connected_pins)==1,'Threat dispatcher uses actual validity')
    check(len(threat_calls)==2,'Forced and random Threat branches integrated')
    check(box_default.get_editor_property('HighValueAmount')==5000 and box_default.get_editor_property('TrashAmount')==3,'Reward amounts preserved')
    report['box_force_outcome_default']=box_default.get_editor_property('bForceOutcome')
    point=next(c for c in t.components(box) if c.get_name().startswith('CreatureSpawnPoint'))
    report['creature_spawn_relative_location']=str(point.get_editor_property('relative_location'))
    spawn_relative=point.get_editor_property('relative_location')
    check(abs(spawn_relative.x-250)<.01 and abs(spawn_relative.y+300)<.01 and abs(spawn_relative.z+3)<.01,'Creature spawn offset avoids immediate attack overlap and pedestal')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    placed=list(unreal.GameplayStatics.get_all_actors_of_class(world,box.generated_class()))
    report['placed_boxes']=[]
    for actor in placed:
        spawn_point=next(c for c in actor.get_components_by_class(unreal.SceneComponent) if c.get_name()=='CreatureSpawnPoint')
        report['placed_boxes'].append({'actor':actor.get_name(),'root':str(actor.get_actor_location()),'spawn':str(spawn_point.get_world_location())})
    nav=list(unreal.GameplayStatics.get_all_actors_of_class(world,unreal.NavMeshBoundsVolume))
    report['navmesh_bounds_volume_count']=len(nav)
    report['world']=world.get_path_name()
    out=ROOT/'Saved/T05/validation.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    unreal.log('[T05] STRUCTURAL PASS - saved assets reloaded; runtime acceptance NOT RUN')

if __name__=='__main__':main()
