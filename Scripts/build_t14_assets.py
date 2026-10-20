"""Build the T14 decision/terminal widget and configure the native coordinator.

Run after build-editor through cpp_migration.py editor. No MCP, PIE or UI control.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Saved/T14'
SPAWNER = '/Game/Anomalies/Containers/BP_BoxSpawner'
WIDGET = '/Game/UI/WBP_RoundDecision'
PLAYER = '/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter'
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
UMG = unreal.get_default_object(unreal.UMGToolSet)


def save(asset):
    BlueprintTools.compile_blueprint(asset, warnings_as_errors=True)
    assert ASSETS.save_loaded_asset(asset, only_if_is_dirty=False), asset.get_path_name()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    backup = OUT / ('AssetBackup_' + datetime.now().strftime('%Y%m%dT%H%M%S%f'))
    backup.mkdir()
    for path in (SPAWNER, WIDGET):
        source = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
        if not source.is_file():
            assert path == WIDGET
            continue
        target = backup / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    widget = ASSETS.load_asset(WIDGET) if ASSETS.does_asset_exist(WIDGET) else None
    if widget is None:
        widget = UMG.call_method('CreateWidgetBlueprint',
                                 ('/Game/UI', 'WBP_RoundDecision', unreal.AnomalyDecisionWidget.static_class()))
    assert widget
    widgets = UMG.call_method('GetWidgets', (widget,)).widgets
    if widgets:
        assert UMG.call_method('RemoveWidget', (widget, widgets[0].widget))
    canvas = UMG.call_method('AddWidget', (widget, unreal.CanvasPanel.static_class(), 'DecisionCanvas', None, -1))
    assert canvas.widget
    text = UMG.call_method('AddWidget', (widget, unreal.TextBlock.static_class(), 'StatusText', canvas.widget, -1))
    assert text.widget
    text.widget.set_text(unreal.Text('当前收益  $0\n完成回合  0    成功收容  0\n\n[1] 继续    [2] 撤离'))
    text.widget.set_font_size(30)
    text.widget.set_editor_property('justification', unreal.TextJustify.CENTER)
    text.widget.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(.92, .96, 1., 1.)))
    text.widget.set_shadow_offset(unreal.Vector2D(2., 2.))
    text.widget.set_shadow_color_and_opacity(unreal.LinearColor(0., 0., 0., 1.))
    slot = text.slot
    slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(.5, .5), maximum=unreal.Vector2D(.5, .5)))
    slot.set_position(unreal.Vector2D(0., 0.))
    slot.set_size(unreal.Vector2D(900., 340.))
    slot.set_alignment(unreal.Vector2D(.5, .5))
    UMG.call_method('ToggleWidgetAsVariable', (widget, text.widget, True))
    assert UMG.call_method('CompileWidgetBlueprint', (widget,))
    save(widget)

    spawner = ASSETS.load_asset(SPAWNER)
    player = ASSETS.load_asset(PLAYER)
    assert spawner and player
    save(spawner)
    defaults = unreal.get_default_object(spawner.generated_class())
    defaults.set_editor_property('decision_widget_class', widget.generated_class())
    defaults.set_editor_property('next_round_delay', 2.)
    assert ASSETS.save_loaded_asset(spawner, only_if_is_dirty=False)
    BlueprintTools.compile_blueprint(player, warnings_as_errors=True)
    report = dict(status='BUILT', backup=str(backup), assets=[SPAWNER, WIDGET],
                  player_compiled=PLAYER, reward_delay=2.0, gameplay_tested=False,
                  scope='T14 native state and UMG assets; no MCP, PIE, screen automation or package')
    (OUT / 'build_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('[T14] BUILD PASS')


main()
