"""Independently reload placed assets, verify navigation and protect accepted gameplay."""
from pathlib import Path
import unreal,json,hashlib,sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'Scripts'))
from t20_layout import MAP,BOX_POINTS,ENTRANCE,START,THREAT_OFFSET
OUT=ROOT/'Saved/ScenePolish'
baseline=json.loads((OUT/'baseline.json').read_text(encoding='utf-8'))
manifest=json.loads((ROOT/'ScenePolishAssets/mesh_manifest.json').read_text(encoding='utf-8'))
build=json.loads((OUT/'build_report.json').read_text(encoding='utf-8'))
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
checks=[]
def check(name,value):
    checks.append(dict(check=name,passed=bool(value)));assert value,name
check('Saved exploration map reload',L.load_level(MAP))
for name,info in manifest['meshes'].items():
    o=A.load_asset('/Game/Prototype/Environment/ScenePolish/'+name)
    check('Static mesh reload '+name,isinstance(o,unreal.StaticMesh))
    bounds=o.get_bounds();dims=[v*2 for v in [bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z]]
    check('Exported centimetre dimensions '+name,max(abs(dims[a]-100*info['dimensions_m'][a]) for a in range(3))<.3)
    check('Assigned palette '+name,all(s.get_editor_property('material_interface') and '/ScenePolish/' in s.get_editor_property('material_interface').get_path_name() for s in o.get_editor_property('static_materials')))
actors=list(E.get_all_level_actors());generated=[o for o in actors if o.actor_has_tag('ScenePolishGenerated')]
check('Generated actor count',len(generated)==build['generated_actors'])
check('Idempotent unique labels',len(generated)==len({o.get_actor_label() for o in generated}))
check('Solid wall-side furniture count',sum(o.static_mesh_component.get_collision_profile_name()=='BlockAll' for o in generated if isinstance(o,unreal.StaticMeshActor))==build['solid_props'])
spawners=[o for o in actors if isinstance(o,unreal.AnomalyRoundCoordinator)]
check('Single exploration authority',len(spawners)==1 and spawners[0].get_editor_property('play_mode')==unreal.AnomalyPlayMode.EXPLORATION)
xyz=lambda v:tuple(round(getattr(v,a),3) for a in ['x','y','z'])
s=spawners[0]
check('Entrance unchanged',xyz(s.get_editor_property('entrance_location'))==ENTRANCE)
check('Threat offset unchanged',xyz(s.get_editor_property('exploration_threat_offset'))==THREAT_OFFSET)
for key,point in zip(['box_point_left','box_point_middle','box_point_right'],BOX_POINTS):
    check('Candidate location unchanged '+key,xyz(s.get_editor_property(key).get_editor_property('relative_location'))==point)
check('No placed runtime crate',not any(isinstance(o,unreal.AnomalyBoxActor) for o in actors))
starts=[o for o in actors if isinstance(o,unreal.PlayerStart)]
check('PlayerStart preserved',len(starts)==1 and xyz(starts[0].get_actor_location())==START)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
tiles=unreal.AnomalyRoundCoordinator.build_exploration_navigation(world)
check('Actual navigation tiles',tiles>0)
for label,(x,y,z) in zip(['A','B','C'],BOX_POINTS):
    path=unreal.NavigationSystemV1.find_path_to_location_synchronously(world,unreal.Vector(0,1700,98),unreal.Vector(x,y-180,98))
    check('Complete entrance-to-room path '+label,path and path.is_valid() and not path.is_partial() and len(path.path_points)>=2)
for rel,digest in baseline['protected'].items():
    assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest,'Protected asset: '+rel
check('All accepted assets protected',True)
(OUT/'reload_report.json').write_text(json.dumps(dict(status='PASS',checks=checks,protected_assets=len(baseline['protected']),navigation_valid_tiles=tiles,generated_actors=len(generated)),ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[SCENE POLISH] RELOAD PASS')
