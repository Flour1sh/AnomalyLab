"""Save T13 native component inheritance into the existing box and coordinator Blueprints.

Run in an unattended, NullRHI editor after the native Editor target compiles.
No MCP, PIE, or screen automation is involved.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Saved/T13'
PATHS = ('/Game/Anomalies/Containers/BP_BoxSpawner',
         '/Game/Anomalies/Containers/BP_AnomalyBox',
         '/Game/UI/WBP_BoxLocked')
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
UMG = unreal.get_default_object(unreal.UMGToolSet)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    backup = OUT / ('AssetBackup_' + datetime.now().strftime('%Y%m%dT%H%M%S%f'))
    backup.mkdir()
    for path in PATHS:
        relative = Path('Content') / (path.removeprefix('/Game/') + '.uasset')
        source = ROOT / relative
        if not source.is_file():
            assert path == '/Game/UI/WBP_BoxLocked', source
            continue
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    spawner, box = (ASSETS.load_asset(path) for path in PATHS[:2])
    assert spawner and box
    assert isinstance(unreal.get_default_object(spawner.generated_class()), unreal.AnomalyRoundCoordinator)
    assert isinstance(unreal.get_default_object(box.generated_class()), unreal.AnomalyBoxActor)
    label = ASSETS.load_asset(PATHS[2]) if ASSETS.does_asset_exist(PATHS[2]) else None
    if label is None:
        label = UMG.call_method('CreateWidgetBlueprint', ('/Game/UI', 'WBP_BoxLocked', unreal.UserWidget.static_class()))
    assert label
    widgets = UMG.call_method('GetWidgets', (label,)).widgets
    if widgets:
        assert UMG.call_method('RemoveWidget', (label, widgets[0].widget))
    item = UMG.call_method('AddWidget', (label, unreal.TextBlock.static_class(), 'LockedText', None, -1))
    assert item.widget
    item.widget.set_text(unreal.Text('已锁定'))
    item.widget.set_font_size(26)
    item.widget.set_editor_property('justification', unreal.TextJustify.CENTER)
    item.widget.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(1., .3, .2, 1.)))
    item.widget.set_shadow_offset(unreal.Vector2D(2., 2.))
    item.widget.set_shadow_color_and_opacity(unreal.LinearColor(0., 0., 0., 1.))
    assert UMG.call_method('CompileWidgetBlueprint', (label,))
    for asset in (label, box, spawner):
        BlueprintTools.compile_blueprint(asset, warnings_as_errors=True)
        assert ASSETS.save_loaded_asset(asset, only_if_is_dirty=False), asset.get_path_name()
    box_defaults = unreal.get_default_object(box.generated_class())
    box_defaults.set_editor_property('locked_widget_class', label.generated_class())
    assert ASSETS.save_loaded_asset(box, only_if_is_dirty=False)
    coordinator = unreal.get_default_object(spawner.generated_class())
    assert coordinator.get_editor_property('box_class') == box.generated_class()
    for prop in ('box_point_left', 'box_point_middle', 'box_point_right'):
        assert coordinator.get_editor_property(prop), prop
    report = dict(status='BUILT', backup=str(backup), assets=PATHS,
                  spawn_points=3, candidate_count=3, gameplay_tested=False,
                  scope='T13 native inheritance; no MCP, PIE, UI automation, or packaging')
    (OUT / 'build_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('[T13] BUILD PASS')


main()
