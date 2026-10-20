"""Independent read-only Observer reference reload."""
import json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[1];checks=[]
def check(name,ok):
    checks.append(dict(check=name,passed=bool(ok)));assert ok,name
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);U=unreal.get_default_object(unreal.UMGToolSet)
cfg=A.load_asset('/Game/Prototype/Observer/DA_ObserverConfig');check('Native Observer config',isinstance(cfg,unreal.AnomalyObserverConfig))
for key,value in dict(observe_distance=2000.,enter_dot=.8,exit_dot=.72,lost_sight_grace=.18,minimum_dwell=.2,acquire_seconds=.08,contact_grace=.35,observation_tolerance=4.,unobservable_seconds=1.25,mixed_pool_weight=.35).items():
    check(key,abs(cfg.get_editor_property(key)-value)<.0001)
for key in ['body_material','eye_material','red_eye_material']:check(key,cfg.get_editor_property(key) is not None)
for r in 'ABC':check('Region '+r,list(map(str,A.load_asset('/Game/Prototype/Data/Regions/DA_Region_'+r).get_editor_property('allowed_anomalies')))==['Chaser','Observer'])
for path,enabled in [('/Game/Prototype/Maps/L_Prototype',True),('/Game/Prototype/Maps/L_LegacyPrototype',False)]:
    check('Load '+path,L.load_level(path));c=next(x for x in E.get_all_level_actors() if isinstance(x,unreal.AnomalyRoundCoordinator))
    check(path+' Observer opt-in',c.get_editor_property('enable_observer_pool')==enabled)
    if enabled:check('Strong config and class references',c.get_editor_property('observer_config')==cfg and c.get_editor_property('observer_class') is not None)
bp=A.load_asset('/Game/UI/WBP_HealthThreat');w={str(x.widget.get_name()):x.widget for x in U.call_method('GetWidgets',(bp,)).widgets if x.widget}
check('Existing health and threat widgets retained','HPText' in w and 'ThreatText' in w and 'DamageText' in w)
check('Two-line Observer status room',w['ThreatText'].slot.get_size()==unreal.Vector2D(600,90))
(ROOT/'Saved/V04/T30/reload_report.json').write_text(json.dumps(dict(status='PASS',checks=checks),ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[T30 Reload] PASS '+str(len(checks)))
