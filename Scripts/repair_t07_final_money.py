"""Connect the existing impure GetMoney before T06ShowEnd; back up first."""
import json
import shutil
from datetime import datetime
from pathlib import Path
from t06_mcp_client import Session

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Saved/T07'
BP = '/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter'
REF = {'refPath': BP + '.BP_FirstPersonCharacter'}
GRAPH = {'refPath': REF['refPath'] + ':T06RunEnded'}
TOOL = 'editor_toolset.toolsets.blueprint.BlueprintTools'
s = Session()
assert not s.editor('IsPIERunning')
nodes = s.call(TOOL, 'find_nodes', graph=GRAPH, title='')
infos = s.call(TOOL, 'get_node_infos', nodes=nodes)
money = next(n for n in infos if n['type_id'] == '|GetMoney')
show = next(n for n in infos if n['type_id'] == '|T06ShowEnd')
def pin(n, direction, name):
    return next(p for p in n[direction + '_pins'] if p['name'] == name)
mi = pin(money, 'input', 'execute')
si = pin(show, 'input', 'execute')
mo = pin(money, 'output', 'then')
if mi['connected_pins']:
    assert mo['pin_id'] in si['connected_pins'], 'Unexpected existing wiring'
    print('Already repaired')
else:
    assert len(si['connected_pins']) == 1
    upstream = si['connected_pins'][0]
    backup = OUT / ('FinalMoneyBackup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup.mkdir()
    shutil.copy2(ROOT / 'Content/FirstPerson/Blueprints/BP_FirstPersonCharacter.uasset', backup)
    (backup / 'graph_before.json').write_text(json.dumps(infos, ensure_ascii=False, indent=2), encoding='utf-8')
    s.call(TOOL, 'break_pins', output_pin=upstream, input_pin=si['pin_id'])
    s.call(TOOL, 'connect_pins', output_pin=upstream, input_pin=mi['pin_id'])
    s.call(TOOL, 'connect_pins', output_pin=mo['pin_id'], input_pin=si['pin_id'])
    s.call(TOOL, 'compile_blueprint', blueprint=REF, warnings_as_errors=True)
    after = s.call(TOOL, 'get_node_infos', nodes=nodes)
    m = next(n for n in after if n['type_id'] == '|GetMoney')
    h = next(n for n in after if n['type_id'] == '|T06ShowEnd')
    assert pin(m, 'input', 'execute')['connected_pins'] == [upstream]
    assert pin(h, 'input', 'execute')['connected_pins'] == [pin(m, 'output', 'then')['pin_id']]
    assert s.call('editor_toolset.toolsets.asset.AssetTools', 'save_assets', asset_paths=[BP])
    (OUT / 'final_money_repaired.json').write_text(json.dumps(after, ensure_ascii=False, indent=2), encoding='utf-8')
    print('GetMoney executes before T06ShowEnd; strict compile PASS; saved character only')
