"""T33 read-only fresh-process inspection. No save, compile or regeneration calls."""
import hashlib
import json
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Saved/V05/T33'
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
checks=[]
def check(name,value):
    checks.append(dict(check=name,passed=bool(value)))
    assert value,name
def xyz(v): return [round(v.x,3),round(v.y,3),round(v.z,3)]
def path(v): return v.get_path_name() if v else None

maps={}
for level in ['L_MainMenu','L_Prototype','L_LegacyPrototype']:
    package='/Game/Prototype/Maps/'+level
    check('Load '+level,L.load_level(package))
    actors=list(E.get_all_level_actors())
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    row=dict(game_mode=path(world.get_world_settings().get_editor_property('default_game_mode')),
             actors=len(actors),player_starts=[dict(label=x.get_actor_label(),location=xyz(x.get_actor_location()),rotation=str(x.get_actor_rotation())) for x in actors if isinstance(x,unreal.PlayerStart)],
             placed_boxes=sum(isinstance(x,unreal.AnomalyBoxActor) for x in actors),
             nav_bounds=sum(isinstance(x,unreal.NavMeshBoundsVolume) for x in actors),
             nav_meshes=sum(isinstance(x,unreal.RecastNavMesh) for x in actors))
    coordinators=[x for x in actors if isinstance(x,unreal.AnomalyRoundCoordinator)]
    check('Coordinator count '+level,len(coordinators)==(0 if level=='L_MainMenu' else 1))
    if coordinators:
        c=coordinators[0]
        row['coordinator']=dict(actor=path(c),play_mode=str(c.get_editor_property('play_mode')),
          use_preparation=c.get_editor_property('use_preparation'),use_region_rules=c.get_editor_property('use_region_rules'),
          progression=path(c.get_editor_property('progression_config')),observer=path(c.get_editor_property('observer_config')),
          balance=path(c.get_editor_property('balance_config')),hud=path(c.get_editor_property('exploration_widget_class')),
          entrance=xyz(c.get_editor_property('entrance_location')),
          points={k:xyz(c.get_editor_property(k).get_world_location()) for k in ['box_point_left','box_point_middle','box_point_right']},
          regions=[path(x) for x in c.get_editor_property('region_rules')])
        check('No placed boxes '+level,row['placed_boxes']==0)
    maps[level]=row
check('v04 preparation enabled',maps['L_Prototype']['coordinator']['use_preparation'])
check('v04 region rules enabled',maps['L_Prototype']['coordinator']['use_region_rules'])
check('v04 single entrance spawn',len(maps['L_Prototype']['player_starts'])==1)
check('Legacy isolated',not maps['L_LegacyPrototype']['coordinator']['use_preparation'])
player=A.load_asset('/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter')
check('Player class',player is not None)
graph=unreal.BlueprintEditorLibrary.find_graph(player,'T06Restart')
check('Restart graph',graph is not None)
nodes=[BlueprintTools._get_node_info(n).type_id for n in BlueprintTools.find_nodes(graph)]
check('Restart reads current level',sum('GetCurrentLevelName' in n for n in nodes)==1)
cfg=A.load_asset('/Game/Prototype/Data/DA_ProgressionConfig')
check('Progression data asset',cfg is not None)
config={k:cfg.get_editor_property(k) for k in ['prices','max_levels','charges_per_level','precision_per_level','precision_cap','decoy_radius','decoy_seconds','decoy_cooldown']}
config['prices']=list(config['prices']); config['max_levels']=list(config['max_levels'])
game_mode=A.load_asset('/Game/FirstPerson/Blueprints/BP_FirstPersonGameMode')
cdo=unreal.get_default_object(game_mode.generated_class())
classes={k:path(cdo.get_editor_property(k)) for k in ['default_pawn_class','player_controller_class','hud_class']}
report=dict(status='PASS',scope='Read-only saved-asset reload, no gameplay or human input',checks=checks,maps=maps,progression=config,game_mode_classes=classes,restart_node_types=nodes)
(OUT/'asset_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[V05 T33 AUDIT] PASS')
