"""T37 only writes new placement data and L_Lab, never accepted maps/assets."""
import json,hashlib
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[1]
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
M=json.loads((ROOT/'Saved/V05/T33/source_copy_manifest.json').read_text(encoding='utf-8'))
old=[r for r in M['files'] if r['path'].startswith('Content/')]
def protected():assert all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in old)
protected()
path='/Game/Prototype/V05/Data/DA_Placement'
asset=A.load_asset(path)
if not asset:
    factory=unreal.DataAssetFactory();factory.set_editor_property('data_asset_class',unreal.AnomalyPlacementConfig)
    asset=unreal.AssetToolsHelpers.get_asset_tools().create_asset('DA_Placement','/Game/Prototype/V05/Data',unreal.AnomalyPlacementConfig,factory)
assert asset
points={
    'APoints':[(-x,y,48) for x in (1150,900,650) for y in (-250,200,650)],
    'BPoints':[(x,y,48) for x in (650,900,1150) for y in (-250,200,650)],
    'CPoints':[(x,y,48) for x in (-450,0,450) for y in (-1250,-1000,-750)],
}
for prop,values in points.items():asset.set_editor_property(prop,[unreal.Vector(*v) for v in values])
assert A.save_loaded_asset(asset,only_if_is_dirty=False)
assert L.load_level('/Game/Maps/L_Lab')
owners=[a for a in E.get_all_level_actors() if isinstance(a,unreal.AnomalyRoundCoordinator)];assert len(owners)==1
owners[0].set_editor_property('PlacementConfig',asset)
assert L.save_current_level()
protected()
report=dict(status='PASS',actor_count=len(E.get_all_level_actors()),points=points,protected_content=len(old),scope='Authored candidates only; runtime legality and fallback validated separately')
out=ROOT/'Saved/V05/T37';out.mkdir(parents=True,exist_ok=True)
(out/'placement_build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('[T37 BUILD] PASS')
