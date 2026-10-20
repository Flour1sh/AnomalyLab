"""Fresh-process curve reference and immutable baseline audit."""
import json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[1];checks=[]
def check(name,ok):checks.append(dict(check=name,passed=bool(ok)));assert ok,name
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cfg=A.load_asset('/Game/Prototype/Data/DA_BalanceConfig');check('Native config',isinstance(cfg,unreal.AnomalyBalanceConfig))
for k,v in dict(threat_per_round=.03,threat_cap=1.15,reward_per_round=.05,reward_cap=1.30).items():check(k,abs(cfg.get_editor_property(k)-v)<1e-10)
for path,on in [('/Game/Prototype/Maps/L_Prototype',True),('/Game/Prototype/Maps/L_LegacyPrototype',False)]:
    check('Load '+path,L.load_level(path));c=next(x for x in E.get_all_level_actors() if isinstance(x,unreal.AnomalyRoundCoordinator))
    check('Curve opt-in '+path,(c.get_editor_property('balance_config')==cfg) if on else c.get_editor_property('balance_config') is None)
    check('Two containments preserved '+path,c.get_editor_property('max_threats')==2)
(ROOT/'Saved/V04/T31/reload_report.json').write_text(json.dumps(dict(status='PASS',checks=checks),ensure_ascii=False,indent=2),encoding='utf-8')
