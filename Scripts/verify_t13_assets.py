"""Independent T13 asset reload and native component inspection; no gameplay."""
import json
from pathlib import Path

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools

ROOT = Path(__file__).resolve().parent.parent
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
spawner = ASSETS.load_asset('/Game/Anomalies/Containers/BP_BoxSpawner')
box = ASSETS.load_asset('/Game/Anomalies/Containers/BP_AnomalyBox')
label = ASSETS.load_asset('/Game/UI/WBP_BoxLocked')
assert spawner and box and label
for asset in (label, box, spawner):
    BlueprintTools.compile_blueprint(asset, warnings_as_errors=True)
coordinator = unreal.get_default_object(spawner.generated_class())
assert coordinator.get_editor_property('box_class') == box.generated_class()
assert unreal.get_default_object(box.generated_class()).get_editor_property('locked_widget_class') == label.generated_class()
points = {}
for name in ('box_point_left', 'box_point_middle', 'box_point_right'):
    component = coordinator.get_editor_property(name)
    assert component
    location = component.get_editor_property('relative_location')
    points[name] = [location.x, location.y, location.z]
assert len({tuple(value) for value in points.values()}) == 3
report = dict(status='PASS', assets=[spawner.get_path_name(), box.get_path_name(), label.get_path_name()],
              points=points, candidate_count=3, gameplay_tested=False,
              scope='Independent asset reload and Blueprint compile only')
(ROOT / 'Saved/T13/reload_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('[T13] RELOAD PASS')
