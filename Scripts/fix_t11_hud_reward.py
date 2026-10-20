"""Replace the legacy fixed +$5,000 result message with the box's actual reward.

Run through cpp_migration.py editor --script fix_t11_hud_reward.py after closing the GUI editor.
"""
import hashlib
import json
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Scripts'))
from cpp_migration import context, journal
from editor_toolset.toolsets.blueprint import BlueprintTools as B
import build_t04 as h
import build_t05 as t

RUN = context()
STAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = ROOT/'Saved/CppMigration/HudRewardFix'/STAMP
OUT.mkdir(parents=True, exist_ok=False)
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
HUD = '/Game/UI/WBP_PrototypeHUD'
CHAR = '/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter'
REPORT = {'status':'RUNNING','backup':str(OUT),'assets':[HUD,CHAR],'checks':[],'errors':[]}

def check(name, condition):
    REPORT['checks'].append({'name':name,'passed':bool(condition)})
    assert condition, name

def asset(path):
    result=ASSETS.load_asset(path)
    check('Load '+path,result is not None)
    return result

def graph(bp,name):
    return next(g for g in B.list_graphs(bp) if g.get_name()==name)

def node_by_type(g, suffix):
    found=[n for n in B.find_nodes(g) if h.norm(str(B._get_node_info(n).type_id).split('|')[-1])==h.norm(suffix)]
    check('Unique '+suffix,len(found)==1)
    return found[0]

def connect(a, ap, b, bp):
    h.connect(a,[ap],b,[bp])

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda:file.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

def backup():
    paths=[]
    for path in (HUD,CHAR):
        source=ROOT/'Content'/(path[6:]+'.uasset')
        check('Source exists '+path,source.is_file())
        target=OUT/'before'/source.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        check('Backup hash '+path,sha(source)==sha(target))
        paths.append({'source':str(source),'backup':str(target),'sha256':sha(source)})
    REPORT['backed_up']=paths
    journal(RUN,'hud_reward_backup',directory=str(OUT),assets=paths)

def save(bp):
    B.compile_blueprint(bp,warnings_as_errors=True)
    for g in B.list_graphs(bp):
        check('No node errors '+bp.get_name()+'/'+g.get_name(),
              not unreal.BlueprintGraphEditor.get_graph_editor(g).list_nodes_with_errors())
    check('Save '+bp.get_name(),ASSETS.save_loaded_asset(bp,only_if_is_dirty=False))

def change_hud():
    hud=asset(HUD)
    g=graph(hud,'ShowOutcome')
    entry=node_by_type(g,'ShowOutcome')
    set_text=next(n for n in B.find_nodes(g)
                  if 'SetText' in str(B._get_node_info(n).type_id)
                  and any('HIGH VALUE +$5,000' in str(p.get_pin_value())
                          for p in unreal.BlueprintEditorLibrary.list_input_pins(n)))
    check('Legacy fixed reward found',set_text is not None)
    B.add_function_param(g,'RewardAmount','int',True)
    amount=unreal.BlueprintGraphEditor.get_graph_editor(g).add_call_function_node('/Script/Engine.KismetTextLibrary:Conv_IntToText')
    connect(entry,'RewardAmount',amount,'Value')
    h.set_default(amount,['bUseGrouping'],True)
    formatter=h.create(g,['FormatText','Format Text','格式化文本'],50,450)
    h.set_default(formatter,['Format'],'HIGH VALUE +${Amount}')
    connect(amount,'ReturnValue',formatter,'Amount')
    connect(formatter,'Result',set_text,'InText')
    save(hud)
    REPORT['checks'].append({'name':'HUD high-value text uses formatted actual amount','passed':True})

def change_character():
    character=asset(CHAR)
    g=graph(character,'HandleOutcomeResolved')
    editor=unreal.BlueprintGraphEditor.get_graph_editor(g)
    old=node_by_type(g,'ShowOutcome')
    editor.remove_nodes([old])
    new=t.node(g,'ShowOutcome')
    entry=node_by_type(g,'HandleOutcomeResolved')
    branch=next(n for n in B.find_nodes(g) if 'IfThenElse' in n.get_class().get_name())
    # The old call was the only consumer of this getter; either existing getter is equivalent.
    hud_get=next(n for n in B.find_nodes(g) if 'GetPrototypeHUD' in str(B._get_node_info(n).type_id))
    connect(branch,'then',new,'execute')
    connect(hud_get,'PrototypeHUD',new,'self')
    connect(entry,'Outcome',new,'Outcome')
    spawner=editor.add_get_member_variable_node('T06Spawner')
    box=editor.add_get_member_variable_node('CurrentBox','/Script/AnomalyLab.AnomalyRoundCoordinator')
    reward=editor.add_get_member_variable_node('HighValueAmount','/Script/AnomalyLab.AnomalyBoxActor')
    connect(spawner,'T06Spawner',box,'self')
    connect(box,'CurrentBox',reward,'self')
    connect(reward,'HighValueAmount',new,'RewardAmount')
    save(character)
    REPORT['checks'].append({'name':'Character passes current box actual reward to HUD','passed':True})

try:
    backup()
    change_hud()
    change_character()
    REPORT['status']='PASS'
except Exception:
    REPORT['status']='FAIL'
    REPORT['errors'].append(traceback.format_exc())
    unreal.log_error('[HUDRewardFix] '+REPORT['errors'][-1])
finally:
    (OUT/'report.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
    journal(RUN,'hud_reward_fix',status=REPORT['status'],directory=str(OUT),errors=REPORT['errors'])
    unreal.log('[HUDRewardFix] '+REPORT['status']+' Report='+str(OUT/'report.json'))
