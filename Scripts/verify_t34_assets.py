"""Read-only fresh editor reload of both real maps and saved role/geometry/nav data."""
import hashlib,json,sys
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Scripts'))
from t34_layout import HUB,LAB,UI,HUB_START,LAB_START
OUT=ROOT/'Saved/V05/T34';A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
checks=[]
def check(n,v):checks.append(dict(check=n,passed=bool(v)));assert v,n
def xyz(v):return tuple(round(x,3) for x in v.to_tuple())
build=json.loads(Path(json.loads((OUT/'latest_build.json').read_text(encoding='utf-8'))['report']).read_text(encoding='utf-8'))
check('Builder second execution was idempotent',build['idempotence_verified'] is True)
bp=A.load_asset(UI);check('Reload Hub UI native parent',bp is not None and isinstance(unreal.get_default_object(bp.generated_class()),unreal.AnomalyHubWidget))
for map_path,start,role in [(HUB,HUB_START,'Hub'),(LAB,LAB_START,'Lab')]:
    check('Real disk .umap '+role,(ROOT/('Content'+map_path.removeprefix('/Game')+'.umap')).is_file())
    check('Reload '+role,L.load_level(map_path));actors=list(E.get_all_level_actors());w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    starts=[x for x in actors if isinstance(x,unreal.PlayerStart)];check('One correct PlayerStart '+role,len(starts)==1 and xyz(starts[0].get_actor_location())==start)
    check('Horizontal hallway view '+role,abs(starts[0].get_actor_rotation().pitch)<.001 and abs(starts[0].get_actor_rotation().yaw+90)<.001)
    labels=[x.get_actor_label() for x in actors if x.get_actor_label().startswith('T34_')];check('Unique owned actors '+role,len(labels)==len(set(labels)))
    check('Saved actor count stable '+role,len(actors)==build['signature'][role.lower()+'_actor_count'])
    check('One NavBounds and dynamic Recast '+role,sum(isinstance(x,unreal.NavMeshBoundsVolume) for x in actors)==1 and sum(isinstance(x,unreal.RecastNavMesh) and x.get_editor_property('runtime_generation')==unreal.RuntimeGenerationType.DYNAMIC for x in actors)==1)
    check('Built navigation tiles persisted in report '+role,build['navigation_tiles'][role.lower()]>0)
    if role=='Hub':
        check('Hub own GameMode',w.get_world_settings().get_editor_property('default_game_mode')==unreal.AnomalyHubGameMode.static_class())
        check('Hub no dangerous gameplay actors',not any(isinstance(x,(unreal.AnomalyRoundCoordinator,unreal.AnomalyBoxActor,unreal.AnomalyThreatCharacter,unreal.AnomalyWorldPickup)) for x in actors))
        terminals=[x for x in actors if isinstance(x,unreal.AnomalyHubTerminal)];check('Exactly four unique station IDs',len(terminals)==4 and len({str(x.get_editor_property('kind')) for x in terminals})==4)
        for x in actors:
            if x.get_actor_label().startswith(('T34_Hub_Floor','T34_Hub_Wall_')) and 'Seam' not in x.get_actor_label():check('BlockAll '+x.get_actor_label(),x.static_mesh_component.get_collision_profile_name()=='BlockAll')
    else:
        c=[x for x in actors if isinstance(x,unreal.AnomalyRoundCoordinator)];check('Lab one retained coordinator',len(c)==1)
        check('Lab launch gate without shop',c[0].get_editor_property('await_level_launch') and not c[0].get_editor_property('use_preparation'))
        check('Lab retained region/progression/observer/balance data',c[0].get_editor_property('use_region_rules') and len(c[0].get_editor_property('region_rules'))==3 and all(c[0].get_editor_property(k) for k in ['progression_config','observer_config','balance_config']))
        check('Lab has no Hub terminal actor',not any(isinstance(x,unreal.AnomalyHubTerminal) for x in actors))
manifest=json.loads((Path(json.loads((ROOT/'Saved/V05/checkpoint_T33_verified.json').read_text(encoding='utf-8'))['snapshot'])/'manifest.json').read_text(encoding='utf-8'))
old=[r for r in manifest['files'] if r['path'].startswith('Content/')]
check('All old Content bytes unchanged',all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in old))
(OUT/'asset_reload.json').write_text(json.dumps(dict(status='PASS',checks=checks,protected_content=len(old),scope='Separate-process asset reload only; runtime nav/input tested separately'),ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[T34 RELOAD] PASS')
