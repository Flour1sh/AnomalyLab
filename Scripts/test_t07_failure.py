"""Isolated box-spawn failure test.
Nonzero final-money regression requires manual play: Wallet is not editable.
Editor BoxClass is restored in finally and no map is saved.
"""
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from t06_mcp_client import Session

OUT = Path(__file__).resolve().parent.parent / 'Saved/T07'
s = Session()
assert not s.editor('IsPIERunning')
actor = s.find('BoxSpawner')[0]
original = s.props(actor, 'BoxClass')
report = {'started_utc': datetime.now(timezone.utc).isoformat(), 'original': original,
          'nonzero_final_money': 'MANUAL: MCP cannot edit Wallet Money', 'snapshots': []}
(OUT / 'failure_restore.json').write_text(json.dumps({'actor': actor, 'values': original}, indent=2), encoding='utf-8')
try:
    assert s.set(actor, BoxClass='None')
    s.editor('StartPIE', options={'bSimulate': False, 'playMode': 'PlayMode_InViewPort', 'warmupSeconds': 0})
    player = s.find('FirstPersonCharacter')[0]
    refs = s.props(player, 'bPC_Wallet', 'prototypeHUD', 't06Spawner', 'characterMovement')
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        status = s.props(refs['t06Spawner'], 'RoundState', 'CurrentSpawnRetryCount', 'bPrototypeError', 'CurrentBox')
        report['snapshots'].append(status)
        if status['RoundState'] == 'Ended':
            break
        time.sleep(1)
    report['player'] = s.props(player, 'bT06Ended')
    report['movement'] = s.props(refs['characterMovement'], 'MovementMode', 'Velocity')
    hud = s.props(refs['prototypeHUD'], 'runEndText', 'moneyText', 'interactionPrompt', 'bT06Ended')
    report['hud'] = hud
    for name in ['runEndText', 'moneyText', 'interactionPrompt']:
        schema = json.loads(s.listprops(hud[name]))
        report[name] = s.props(hud[name], *[key for key in ['text', 'visibility'] if key in schema])
    report['boxes'] = s.find('AnomalyBox')
    assert status['RoundState'] == 'Ended' and status['CurrentSpawnRetryCount'] == 3
    assert report['player']['bT06Ended'] and not report['boxes']
    assert 'PROTOTYPE ERROR' in report['runEndText']['text'], report['runEndText']
    report['result'] = 'PASS'
finally:
    s.editor('StopPIE')
    assert s.set(actor, **original)
    report['restored'] = s.props(actor, 'BoxClass')
    assert report['restored'] == original
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (OUT / 'failure_test.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False), flush=True)
