"""Idempotent bounded curve asset; preserves all unrelated Content."""
import json,shutil,hashlib
from pathlib import Path
from datetime import datetime
import unreal
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Saved/V04/T31'/('Assets_'+datetime.now().strftime('%Y%m%dT%H%M%S%f'));OUT.mkdir(parents=True)
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);T=unreal.AssetToolsHelpers.get_asset_tools()
mutable=['Content/Prototype/Maps/L_Prototype.umap','Content/Prototype/Data/DA_BalanceConfig.uasset']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'Content').rglob('*') if p.is_file() and p.relative_to(ROOT).as_posix() not in mutable}
for rel in mutable:
    p=ROOT/rel
    if p.exists():q=OUT/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
path='/Game/Prototype/Data/DA_BalanceConfig';cfg=A.load_asset(path) if A.does_asset_exist(path) else None
if not cfg:
    f=unreal.DataAssetFactory();f.set_editor_property('data_asset_class',unreal.AnomalyBalanceConfig.static_class())
    cfg=T.create_asset('DA_BalanceConfig','/Game/Prototype/Data',unreal.AnomalyBalanceConfig.static_class(),f)
values=dict(threat_per_round=.03,threat_cap=1.15,reward_per_round=.05,reward_cap=1.30)
for k,v in values.items():cfg.set_editor_property(k,v)
assert A.save_loaded_asset(cfg,only_if_is_dirty=False)
assert L.load_level('/Game/Prototype/Maps/L_Prototype');c=next(x for x in E.get_all_level_actors() if isinstance(x,unreal.AnomalyRoundCoordinator))
c.set_editor_property('balance_config',cfg);assert L.save_current_level();unreal.AnomalyRoundCoordinator.finish_asset_compilation()
assert all(sha(ROOT/rel)==digest for rel,digest in protected.items()),'Unrelated Content changed'
(OUT/'report.json').write_text(json.dumps(dict(status='PASS',config=values,changed=mutable,protected_files=len(protected)),ensure_ascii=False,indent=2),encoding='utf-8')
