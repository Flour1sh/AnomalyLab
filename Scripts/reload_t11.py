"""Fresh-process asset load/compile inspection only. Never runs gameplay."""
import sys
import json
import traceback
from pathlib import Path
import unreal
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'Scripts'))
import build_t11 as build
from t11_data import ROWS, FIELDS, validate_rows
h, B, t, OUT = build.h, build.B, build.t, build.OUT
report = dict(status='RUNNING',checks=[],runtime='NOT RUN',PIE='NOT RUN',MCP='NOT USED',screen_control='NOT USED')


def check(name, passed):
    report['checks'].append(dict(name=name,passed=bool(passed)))
    assert passed, name


def main():
    definition, bp = h.load(build.DEFINITION), h.load(h.BOX_PATH)
    t.compile_bp(definition)
    check('Definition schema compiles',True)
    rows = []
    for row in ROWS:
        asset = h.load(build.DATA_DIR+'/DA_Box_'+row['Name'])
        actual = {'Name':row['Name']}
        for name, kind in FIELDS.items():
            value = asset.get_editor_property(name)
            actual[name] = str(value) if kind in ('name','text') else value
        rows.append(actual)
    validate_rows(rows)
    check('All six saved definitions match authoring data',rows==ROWS or sorted(rows,key=lambda r:r['Name'])==sorted(ROWS,key=lambda r:r['Name']))
    check('Build marker',h.ASSETS.get_metadata_tag(bp,'T11BuildVersion')=='1')
    t.compile_bp(bp)
    check('Box compiles with warnings treated as errors',True)
    for name in build.FUNCTIONS:
        graph = next(g for g in B.list_graphs(bp) if g.get_name()==name)
        check('Nonempty function '+name,len(B.find_nodes(graph))>2)
    cdo = unreal.get_default_object(bp.generated_class())
    for name, expected in dict(bDefinitionInitialized=False,bDefinitionValid=False,bUseFixedSeeds=False,
                               bForceOutcome=False,HighValueAmount=0,TrashAmount=3,RevealDelay=1.0,bOpened=False,bResolved=False).items():
        check('Saved default '+name,cdo.get_editor_property(name)==expected)
    check('Normal play chooses random public definition',str(cdo.get_editor_property('DefinitionID'))=='None')
    g = unreal.BlueprintEditorLibrary.find_event_graph(bp)
    nodes = B.find_nodes(g)
    types = [str(B._get_node_info(n).type_id).split('|')[-1] for n in nodes]
    check('BeginPlay initialization wired',types.count('T11InitializeDefinition')==2)
    check('One weighted outcome call',types.count('T11RollOutcome')==1)
    check('Both HighValue paths cache reward once',types.count('T11RollReward')==2)
    check('Four original wallet call sites retained',types.count('AddMoney')==4)
    check('No global outcome RNG remains in EventGraph','RandomIntegerInRange' not in types)
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.wait_for_completion()
    options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=True)
    for path in [build.DEFINITION,h.BOX_PATH]+[build.DATA_DIR+'/DA_Box_'+r['Name'] for r in ROWS]:
        missing = [str(d) for d in registry.get_dependencies(path,options) if str(d).startswith('/Game/') and not h.ASSETS.does_asset_exist(str(d))]
        check('Direct game references resolve '+path,not missing)
    for path in ('/Game/Anomalies/Containers/BP_BoxSpawner','/Game/Core/Components/BPC_Wallet','/Game/Anomalies/Creatures/BP_Spider','/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter'):
        t.compile_bp(h.load(path))
        check('Dependent blueprint compiles '+path,True)
    baseline = json.loads((OUT/'baseline.json').read_text(encoding='utf-8'))['hashes']
    current = build.hashes()
    changed = [p for p,v in baseline.items() if current.get(p)!=v]
    added = [p for p in current if p not in baseline]
    report.update(changed_files=changed,added_files=added)
    check('Only original box package changed',changed==['Content\\Anomalies\\Containers\\BP_AnomalyBox.uasset'])
    expected = {'Content\\Prototype\\Data\\Boxes\\BP_AnomalyBoxDefinition.uasset'} | {'Content\\Prototype\\Data\\Boxes\\DA_Box_'+r['Name']+'.uasset' for r in ROWS}
    check('Only seven new definition packages',set(added)==expected)
    report['status']='PASS'


try:
    main()
except Exception:
    report['status']='FAIL'
    report['error']=traceback.format_exc()
    unreal.log_error('[T11] FAIL '+report['error'])
finally:
    (OUT/'reload.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    unreal.log('[T11] RELOAD '+report['status']+'; gameplay tests NOT RUN')
