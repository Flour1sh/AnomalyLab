"""Independent process reload; no asset saving or generation."""
import json,hashlib,sys
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'Scripts'))
from t26_data import REGIONS
OUT=ROOT/'Saved/V04/T26'
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
U=unreal.get_default_object(unreal.UMGToolSet)
checks=[]
def check(name,value):
    checks.append(dict(check=name,passed=bool(value))); assert value,name
try:
    check('Exploration reload',L.load_level('/Game/Prototype/Maps/L_Prototype'))
    c=next(a for a in E.get_all_level_actors() if isinstance(a,unreal.AnomalyRoundCoordinator))
    check('Enabled only in exploration',c.get_editor_property('use_region_rules') and c.get_editor_property('play_mode')==unreal.AnomalyPlayMode.EXPLORATION)
    regions=c.get_editor_property('region_rules'); check('Three regions',len(regions)==3)
    for r,expected in zip(regions,REGIONS):
        for key,value in expected.items():
            actual=r.get_editor_property(key)
            actual=list(actual) if isinstance(value,list) else str(actual) if isinstance(value,str) else actual
            check(expected['region_id']+'/'+key,actual==value)
        check('Chaser permitted',list(map(str,r.get_editor_property('allowed_anomalies')))==['Chaser'])
    check('Fixed seed off',not c.get_editor_property('use_fixed_region_seed'))
    check('Empty telemetry',not c.get_editor_property('region_stats'))
    bp=A.load_asset('/Game/UI/WBP_ExplorationPrompt')
    BlueprintTools.compile_blueprint(bp,warnings_as_errors=True)
    check('HUD compiled',bp.get_editor_property('status')==unreal.BlueprintStatus.BS_UP_TO_DATE)
    widgets=[str(w.widget.get_name()) for w in U.call_method('GetWidgets',(bp,)).widgets if w.widget]
    check('Old and new widgets retained exactly once',all(widgets.count(name)==1 for name in
        ('RegionText','RegionBacking','DamageVeil','Crosshair','InteractionPrompt','ExplorationObjective','InventoryText','NoticeText','PromptBacking','NoticeBacking')))
    check('Legacy reload',L.load_level('/Game/Prototype/Maps/L_LegacyPrototype'))
    legacy=next(a for a in E.get_all_level_actors() if isinstance(a,unreal.AnomalyRoundCoordinator))
    check('Legacy opt-out',not legacy.get_editor_property('use_region_rules') and not legacy.get_editor_property('region_rules'))
    old=json.loads((OUT/'assets.json').read_text(encoding='utf-8'))
    check('All protected content hashes unchanged',all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in old['protected_sha256'].items()))
    status='PASS'
except Exception:
    status='FAIL'; raise
finally:
    (OUT/'reload.json').write_text(json.dumps(dict(status=status,checks=checks),ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[T26 RELOAD] PASS')
