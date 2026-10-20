"""Fresh-process read-only reload of the actual shop/map/UMG references."""
import json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[1]; checks=[]
def check(name,ok):
    checks.append(dict(check=name,passed=bool(ok))); assert ok,name
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem); L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); U=unreal.get_default_object(unreal.UMGToolSet)
cfg=A.load_asset('/Game/Prototype/Data/DA_ProgressionConfig'); check('Config native class',isinstance(cfg,unreal.AnomalyProgressionConfig))
for k,v in dict(prices=[1000,1500,2500,600],max_levels=[2,2,1,1],charges_per_level=1,precision_per_level=.25,precision_cap=.5,decoy_radius=1200.,decoy_seconds=5.,decoy_cooldown=3.).items():
    value=cfg.get_editor_property(k); check(k,list(value)==v if isinstance(v,list) else value==v)
for path,enabled in [('/Game/Prototype/Maps/L_Prototype',True),('/Game/Prototype/Maps/L_LegacyPrototype',False)]:
    check('load '+path,L.load_level(path)); c=next(x for x in E.get_all_level_actors() if isinstance(x,unreal.AnomalyRoundCoordinator))
    check(path+' preparation scope',c.get_editor_property('use_preparation')==enabled)
    if enabled: check('Strong config reference',c.get_editor_property('progression_config')==cfg)
bp=A.load_asset('/Game/UI/WBP_ExplorationPrompt'); w={str(x.widget.get_name()):x.widget for x in U.call_method('GetWidgets',(bp,)).widgets if x.widget}
for name in ['RegionText','InventoryText','ShopText','ShopBacking','MetaText','DamageVeil','InteractionPrompt']: check('Preserved/added '+name,name in w)
check('Shop list room for Chinese lines',w['ShopText'].slot.get_size()==unreal.Vector2D(1320,650))
out=ROOT/'Saved/V04/T28/reload_report.json'; out.write_text(json.dumps(dict(status='PASS',checks=checks),ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[T28 Reload] PASS '+str(len(checks)))
