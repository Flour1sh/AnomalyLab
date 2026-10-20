"""Independent UE reload of production assets, Blueprint compilation and native defaults."""
import json, hashlib
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
ROOT=Path(__file__).resolve().parent.parent
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
U=unreal.get_default_object(unreal.UMGToolSet)
checks=[]
def check(name,value):
    checks.append(dict(check=name,passed=bool(value)))
    assert value,name
try:
    check('Load production exploration map',L.load_level('/Game/Prototype/Maps/L_Prototype'))
    actors=E.get_all_level_actors()
    coordinators=[a for a in actors if isinstance(a,unreal.AnomalyRoundCoordinator)]
    check('Single exploration coordinator',len(coordinators)==1 and coordinators[0].get_editor_property('play_mode')==unreal.AnomalyPlayMode.EXPLORATION)
    c=coordinators[0]
    definitions=c.get_editor_property('loot_definitions')
    check('Four unique item definitions',len(definitions)==4 and len({str(d.get_editor_property('item_id')) for d in definitions})==4)
    for d in definitions:
        check(d.get_name()+' appearance/pickability',d.get_editor_property('mesh') and d.get_editor_property('material') and d.get_editor_property('pickable'))
        if d.get_editor_property('trash'): check('Trash consistently worth 3',d.get_editor_property('trash_value')==3)
    sounds=c.get_editor_property('feedback_sounds')
    check('All nine feedback sound references saved',len(sounds)==9)
    for name,sound in sounds.items(): check(str(name)+' sound duration positive',sound and sound.get_editor_property('duration')>0)
    check('No test state persisted',c.get_editor_property('settlement_count')==0 and not c.get_editor_property('settlement_done') and not c.get_editor_property('world_loot'))
    points=[c.get_editor_property(n).get_world_location() for n in ('box_point_left','box_point_middle','box_point_right')]
    check('Three points spatially separated',min(points[i].distance(points[j]) for i in range(3) for j in range(i+1,3))>1000)
    for path in ['/Game/Anomalies/Containers/BP_AnomalyBox','/Game/Anomalies/Containers/BP_BoxSpawner',
                 '/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter','/Game/UI/WBP_ExplorationPrompt',
                 '/Game/UI/WBP_RoundDecision','/Game/UI/Menu/WBP_MainMenu']:
        bp=A.load_asset(path)
        check('Load '+path,bp)
        BlueprintTools.compile_blueprint(bp,warnings_as_errors=True)
        check('Compile '+path,bp.get_editor_property('status')==unreal.BlueprintStatus.BS_UP_TO_DATE)
    box=unreal.get_default_object(A.load_asset('/Game/Anomalies/Containers/BP_AnomalyBox').generated_class())
    check('Production RNG/debug defaults',not box.get_editor_property('force_outcome') and not box.get_editor_property('use_fixed_seeds'))
    bp=A.load_asset('/Game/UI/WBP_ExplorationPrompt')
    names=[str(w.widget.get_name()) for w in U.call_method('GetWidgets',(bp,)).widgets if w.widget]
    check('Inventory/prompt/damage/crosshair widgets unique',all(names.count(n)==1 for n in ('InventoryText','InteractionPrompt','ExplorationObjective','NoticeText','DamageVeil','Crosshair')))
    old=json.loads((ROOT/'Saved/T20/build_report.json').read_text(encoding='utf-8'))
    check('Legacy map original bytes unchanged',hashlib.sha256((ROOT/'Content/Prototype/Maps/L_LegacyPrototype.umap').read_bytes()).hexdigest()==old['legacy_sha256'])
    nav=unreal.AnomalyRoundCoordinator.build_exploration_navigation(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world())
    check('Navigation has actual generated tiles',nav>0)
    status='PASS'
except Exception:
    status='FAIL'
    raise
finally:
    (ROOT/'Saved/V03/reload_report.json').write_text(json.dumps(dict(status=status,checks=checks),ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[V03 RELOAD] PASS')

