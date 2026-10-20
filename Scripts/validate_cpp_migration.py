"""Fresh-process native/Blueprint compatibility and protected-source inspection, without saving."""
import hashlib
import json
import sys
import traceback
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'Scripts'))
from cpp_migration import context,journal,write
from prepare_t07 import PACKAGES
from t11_data import FIELDS,ROWS
from editor_toolset.toolsets.blueprint import BlueprintTools as B
from editor_toolset.toolsets.actor import ActorTools as A
RUN=context();OUT=Path(RUN['directory'])
ASSETS=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
REPORT=dict(status='RUNNING',checks=[],errors=[],PIE='NOT RUN',physical_input='NOT RUN',visual_validation='NOT RUN')


def check(name,condition,actual=None):
    REPORT['checks'].append(dict(check=name,passed=bool(condition),actual=actual))
    assert condition,name


def load(path):
    obj=ASSETS.load_asset(path);check('Load '+path,obj is not None);return obj


def main():
    parents={
        '/Game/Prototype/Data/Boxes/BP_AnomalyBoxDefinition':unreal.AnomalyBoxDefinition.static_class(),
        '/Game/Core/Components/BPC_Wallet':unreal.AnomalyWalletComponent.static_class(),
        '/Game/Anomalies/Containers/BP_AnomalyBox':unreal.AnomalyBoxActor.static_class(),
        '/Game/Anomalies/Creatures/BP_Spider':unreal.AnomalyThreatCharacter.static_class(),
        '/Game/Anomalies/Containers/BP_BoxSpawner':unreal.AnomalyRoundCoordinator.static_class()}
    for path,parent in parents.items():
        bp=load(path)
        check('Native parent '+path,bp.get_blueprint_parent_class()==parent)
        check('Migration marker '+path,ASSETS.get_metadata_tag(bp,'CppMigrationVersion')=='1')
    compiled=[];loaded={}
    for rel in PACKAGES:
        if rel.endswith('/L_Prototype'):continue
        path='/Game/'+rel;obj=load(path);loaded[path]=obj
        if isinstance(obj,unreal.Blueprint):
            B.compile_blueprint(obj,warnings_as_errors=True)
            check('Compile '+path,all(not unreal.BlueprintGraphEditor.get_graph_editor(g).list_nodes_with_errors() for g in B.list_graphs(obj)))
            compiled.append(path)
    definition=load('/Game/Prototype/Data/Boxes/BP_AnomalyBoxDefinition');B.compile_blueprint(definition,warnings_as_errors=True)
    for row in ROWS:
        obj=load('/Game/Prototype/Data/Boxes/DA_Box_'+row['Name'])
        check('Native definition instance '+row['Name'],isinstance(obj,unreal.AnomalyBoxDefinition))
        actual={k:str(obj.get_editor_property(k)) if kind in ('name','text') else obj.get_editor_property(k) for k,kind in FIELDS.items()}
        check('Definition values unchanged '+row['Name'],actual=={k:row[k] for k in FIELDS})
    box=loaded['/Game/Anomalies/Containers/BP_AnomalyBox'];cdo=unreal.get_default_object(box.generated_class())
    for key,expected in dict(bOpened=False,bResolved=False,bForceOutcome=False,bUseFixedSeeds=False,RevealDelay=1.0,TrashAmount=3,bDefinitionInitialized=False,bDefinitionValid=False).items():
        check('Box default '+key,cdo.get_editor_property(key)==expected)
    check('All six native definitions referenced',len(cdo.get_editor_property('Definitions'))==6)
    check('No old T11 gameplay function bodies',not any(g.get_name().startswith('T11') for g in B.list_graphs(box)))
    wallet=loaded['/Game/Core/Components/BPC_Wallet']
    check('Native wallet starts at zero',unreal.get_default_object(wallet.generated_class()).get_editor_property('Money')==0)
    check('No duplicate Blueprint Money property','Money' not in [str(n) for n in B.list_variables(wallet)])
    spider=loaded['/Game/Anomalies/Creatures/BP_Spider'];s=unreal.get_default_object(spider.generated_class())
    for key,expected in dict(MoveSpeed=350.0,AcceptanceRadius=80.0,AutoResolveDelay=3.0,bAutoResolveThreat=True,T10MotionScale=1.0).items():
        check('Threat baseline '+key,s.get_editor_property(key)==expected)
    check('Native ResolveThreat replaces graph',not any(g.get_name()=='ResolveThreat' for g in B.list_graphs(spider)))
    baseline=json.loads((OUT/'pre_migration_assets.json').read_text(encoding='utf-8'))
    for name in ('T10FacePlayer','T10AnimateBody'):
        graph=next(g for g in B.list_graphs(spider) if g.get_name()==name)
        actual=[dict(name=n.get_name(),type=str(B._get_node_info(n).type_id),pins=[dict(name=str(p.get_pin_name()),value=str(p.get_pin_value()),links=[q.get_owning_node().get_name()+'.'+str(q.get_pin_name()) for q in p.list_connected_pins()]) for p in list(unreal.BlueprintEditorLibrary.list_input_pins(n))+list(unreal.BlueprintEditorLibrary.list_output_pins(n))]) for n in B.find_nodes(graph)]
        check('T10 cosmetic graph unchanged '+name,actual==baseline['/Game/Anomalies/Creatures/BP_Spider']['graphs'][name])
    manifest=json.loads((OUT/'baseline_manifest.json').read_text(encoding='utf-8'))
    allowed={p[6:]+'.uasset' for p in parents}|{'Prototype/Data/Boxes/DA_Box_'+r['Name']+'.uasset' for r in ROWS}
    changes=[];unexpected=[]
    for entry in manifest['files']:
        rel=entry['path']
        if not rel.startswith(('Content/','Config/')):continue
        path=ROOT/rel
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
            changes.append(rel)
            if not rel.startswith('Content/') or rel[8:] not in allowed:unexpected.append(rel)
    known={e['path'] for e in manifest['files']}
    additions=[p.relative_to(ROOT).as_posix() for folder in ('Content','Config') for p in (ROOT/folder).rglob('*') if p.is_file() and p.relative_to(ROOT).as_posix() not in known]
    REPORT['changed_content_config']=changes;REPORT['added_content_config']=additions
    check('Only planned migration packages changed',not unexpected,unexpected)
    check('No unrelated new content/config',not additions,additions)
    project=json.loads((ROOT/'我的项目3.uproject').read_text(encoding='utf-8-sig'))
    original=json.loads((Path(RUN['backup'])/'source/我的项目3.uproject').read_text(encoding='utf-8-sig'))
    modules=project.pop('Modules',None)
    check('Only runtime module added to project settings',project==original and modules==[dict(Name='AnomalyLab',Type='Runtime',LoadingPhase='Default')])
    registry=unreal.AssetRegistryHelpers.get_asset_registry();registry.wait_for_completion()
    options=unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=True)
    missing=[]
    for path in list(loaded)+list(parents)+['/Game/Prototype/Data/Boxes/DA_Box_'+r['Name'] for r in ROWS]:
        for dependency in registry.get_dependencies(path,options):
            if str(dependency).startswith('/Game/') and not ASSETS.does_asset_exist(str(dependency)):missing.append(str(dependency))
    check('Direct Game dependencies resolve',not missing,missing)
    levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    check('Map loads',levels.load_level('/Game/Prototype/Maps/L_Prototype'))
    actors=list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
    check('Map instance uses native round base',sum(isinstance(a,unreal.AnomalyRoundCoordinator) for a in actors)==1)
    REPORT['compiled_blueprints']=compiled
    REPORT['status']='PASS'


try:main()
except Exception:
    REPORT['status']='FAIL';REPORT['errors'].append(traceback.format_exc());unreal.log_error('[MIGRATION] FAIL '+REPORT['errors'][-1])
finally:
    write(OUT/'reload_validation.json',REPORT)
    journal(RUN,'fresh_reload_validation',status=REPORT['status'],checks=len(REPORT['checks']),errors=REPORT['errors'])
    unreal.log('[MIGRATION] RELOAD '+REPORT['status'])
