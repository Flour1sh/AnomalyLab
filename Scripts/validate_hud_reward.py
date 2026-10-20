"""Fresh-process, read-only validation for the random high-value HUD message."""
import json
import sys
import traceback
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
from cpp_migration import context,journal
from editor_toolset.toolsets.blueprint import BlueprintTools as B

RUN=context()
OUT=sorted((ROOT/'Saved/CppMigration/HudRewardFix').iterdir())[-1]
ASSETS=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
REPORT={'status':'RUNNING','checks':[],'errors':[]}

def check(name,condition):
    REPORT['checks'].append({'name':name,'passed':bool(condition)})
    assert condition,name

def nodes(path,name):
    bp=ASSETS.load_asset(path)
    check('Load '+path,bp is not None)
    B.compile_blueprint(bp,warnings_as_errors=True)
    check('Compile '+path,all(not unreal.BlueprintGraphEditor.get_graph_editor(g).list_nodes_with_errors() for g in B.list_graphs(bp)))
    graph=next(g for g in B.list_graphs(bp) if g.get_name()==name)
    return list(B.find_nodes(graph))

def typeid(node): return str(B._get_node_info(node).type_id)
def outputs(node): return list(unreal.BlueprintEditorLibrary.list_output_pins(node))
def inputs(node): return list(unreal.BlueprintEditorLibrary.list_input_pins(node))
def pin(node,name):
    return next(p for p in inputs(node)+outputs(node) if str(p.get_pin_name())==name)
def connected(a,ap,b,bp):
    return pin(b,bp) in pin(a,ap).list_connected_pins()

try:
    hud=nodes('/Game/UI/WBP_PrototypeHUD','ShowOutcome')
    entry=next(n for n in hud if typeid(n).endswith('|ShowOutcome'))
    formatter=next(n for n in hud if n.get_class().get_name()=='K2Node_FormatText'
                   and 'HIGH VALUE +${Amount}' in str(pin(n,'Format').get_pin_value()))
    totext=next(n for n in hud if any(str(p.get_pin_name())=='Value' and pin(entry,'RewardAmount') in p.list_connected_pins() for p in inputs(n)))
    settext=next(n for n in hud if any(str(p.get_pin_name())=='InText' and pin(formatter,'Result') in p.list_connected_pins() for p in inputs(n)))
    check('HUD formats actual input amount',connected(totext,'ReturnValue',formatter,'Amount'))
    check('HUD high-value SetText uses formatted amount',settext is not None)
    character=nodes('/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter','HandleOutcomeResolved')
    call=next(n for n in character if typeid(n).endswith('|ShowOutcome'))
    reward=next(n for n in character if 'GetHighValueAmount' in typeid(n))
    box=next(n for n in character if 'GetCurrentBox' in typeid(n))
    spawner=next(n for n in character if 'GetT06Spawner' in typeid(n) and connected(n,'T06Spawner',box,'self'))
    check('Character passes current box reward',connected(box,'CurrentBox',reward,'self') and
          connected(reward,'HighValueAmount',call,'RewardAmount') and spawner is not None)
    REPORT['status']='PASS'
except Exception:
    REPORT['status']='FAIL';REPORT['errors'].append(traceback.format_exc())
    unreal.log_error('[HUDRewardValidate] '+REPORT['errors'][-1])
finally:
    (OUT/'reload.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
    journal(RUN,'hud_reward_reload',status=REPORT['status'],checks=len(REPORT['checks']),errors=REPORT['errors'])
    unreal.log('[HUDRewardValidate] '+REPORT['status'])
