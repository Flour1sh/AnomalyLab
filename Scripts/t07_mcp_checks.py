"""Bounded T07 MCP checks; no UI automation or asset saves."""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from t06_mcp_client import Session

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Saved/T07'
s = Session()
report = {'started_utc': datetime.now(timezone.utc).isoformat(), 'compile': [], 'PIE': {}}
if '--resume' in sys.argv:
    report = json.loads((OUT / 'mcp_checks.json').read_text(encoding='utf-8'))
    report['PIE'] = {}


def save():
    (OUT / 'mcp_checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def ref(path):
    return {'refPath': path}


if s.editor('IsPIERunning'):
    raise RuntimeError('Existing PIE session; do not interrupt user play.')
report['level'] = s.call('editor_toolset.toolsets.scene.SceneTools', 'get_current_level')
assert report['level'] == '/Game/Prototype/Maps/L_Prototype'
report['editor_spawners'] = s.find('BoxSpawner')
report['editor_boxes'] = s.find('AnomalyBox')
for path in ['Core/Debug/BFL_PrototypeLog', 'Interaction/BPI_Interactable',
             'Core/Components/BPC_Interaction', 'Core/Components/BPC_Wallet',
             'Anomalies/Loot/BP_Loot_HighValue', 'Anomalies/Loot/BP_Loot_Trash',
             'Anomalies/Creatures/BP_Spider', 'Anomalies/Containers/BP_AnomalyBox',
             'Anomalies/Containers/BP_BoxSpawner', 'UI/WBP_PrototypeHUD',
             'FirstPerson/Blueprints/BP_FirstPersonCharacter']:
    full = '/Game/' + path
    if any(row['asset'] == full for row in report['compile']):
        continue
    result = s.call('editor_toolset.toolsets.blueprint.BlueprintTools', 'compile_blueprint',
                    blueprint=ref(full + '.' + full.rsplit('/', 1)[1]), warnings_as_errors=True)
    report['compile'].append({'asset': full, 'result': result})
    save()
    print('COMPILED', full, result, flush=True)
try:
    s.editor('StartPIE', options={'bSimulate': False, 'playMode': 'PlayMode_InViewPort', 'warmupSeconds': 1})
    p = report['PIE']
    for name in ['BoxSpawner', 'AnomalyBox', 'FirstPersonCharacter', 'Spider', 'Loot_']:
        p[name] = s.find(name)
    for obj in p['BoxSpawner']:
        p['spawner'] = s.props(obj, 'CurrentBox', 'CurrentOutcomeActor', 'CurrentSpider', 'RoundState',
                               'ThreatsResolved', 'MaxThreats', 'CurrentSpawnRetryCount', 'BoxClass')
    for obj in p['AnomalyBox']:
        p['box'] = s.props(obj, 'bOpened', 'bResolved', 'bForceOutcome', 'RevealDelay')
    for obj in p['FirstPersonCharacter']:
        p['player_properties'] = s.listprops(obj)
    save()
    print(json.dumps(p, ensure_ascii=False), flush=True)
finally:
    s.editor('StopPIE')
    report['PIE_stopped'] = not s.editor('IsPIERunning')
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    save()
