import json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[1]
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert L.load_level('/Game/Maps/L_Lab')
owners=[x for x in E.get_all_level_actors() if isinstance(x,unreal.AnomalyRoundCoordinator)];assert len(owners)==1
config=owners[0].get_editor_property('PlacementConfig');assert config and config.get_path_name()=='/Game/Prototype/V05/Data/DA_Placement.DA_Placement'
counts={name:len(config.get_editor_property(name)) for name in ['APoints','BPoints','CPoints']};assert all(n==9 for n in counts.values())
report=dict(status='PASS',counts=counts,actors=len(E.get_all_level_actors()),fresh_process=True)
(ROOT/'Saved/V05/T37/placement_reload.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('[T37 RELOAD] PASS')
