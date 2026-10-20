"""Build T12 assets via unattended UE Python; no MCP, PIE or UI automation.

Compile the native Editor module first with cpp_migration.py build-editor.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import unreal
from editor_toolset.toolsets.actor import ActorTools
from editor_toolset.toolsets.blueprint import BlueprintTools

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Saved/T12'
PLAYER = '/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter'
SCANNER = '/Game/Core/Components/BPC_Scanner'
PANEL = '/Game/UI/WBP_ScanPanel'
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
UMG = unreal.get_default_object(unreal.UMGToolSet)


def save(bp):
    BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)
    assert ASSETS.save_loaded_asset(bp, only_if_is_dirty=False), bp.get_path_name()


def backup():
    folder = OUT / ('AssetBackup_' + datetime.now().strftime('%Y%m%dT%H%M%S%f'))
    folder.mkdir(parents=True)
    for path in (PLAYER, SCANNER, PANEL):
        relative = Path('Content') / (path.removeprefix('/Game/') + '.uasset')
        if (ROOT / relative).is_file():
            dest = folder / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, dest)
    return folder


def add(bp, cls, name, parent=None):
    item = UMG.call_method('AddWidget', (bp, cls.static_class(), name, parent, -1))
    assert item.widget, name
    return item


def slot(item, anchor, position, size, alignment=(0., 0.)):
    item.slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(*anchor), maximum=unreal.Vector2D(*anchor)))
    item.slot.set_position(unreal.Vector2D(*position))
    item.slot.set_size(unreal.Vector2D(*size))
    item.slot.set_alignment(unreal.Vector2D(*alignment))


def panel():
    bp = ASSETS.load_asset(PANEL) if ASSETS.does_asset_exist(PANEL) else None
    if not bp:
        bp = UMG.call_method('CreateWidgetBlueprint', ('/Game/UI', 'WBP_ScanPanel', unreal.AnomalyScanWidget.static_class()))
    assert bp
    # Only rebuild our own isolated panel, never the accepted prototype HUD.
    tree = UMG.call_method('GetWidgets', (bp,))
    if tree.widgets:
        assert UMG.call_method('RemoveWidget', (bp, tree.widgets[0].widget))
    canvas = add(bp, unreal.CanvasPanel, 'ScanCanvas').widget
    summary = add(bp, unreal.TextBlock, 'ScanSummary', canvas)
    summary.widget.set_text(unreal.Text('当前箱子 · 扫描记录\n\n高价值金额：未扫描\n\n威胁可能性：未扫描\n\n高价值可能性：未扫描'))
    summary.widget.set_font_size(20)
    summary.widget.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(.80, .95, .87, 1.)))
    summary.widget.set_shadow_offset(unreal.Vector2D(1., 1.))
    summary.widget.set_shadow_color_and_opacity(unreal.LinearColor(0., 0., 0., 1.))
    summary.widget.set_visibility(unreal.SlateVisibility.COLLAPSED)
    slot(summary, (0., .5), (32., 0.), (410., 370.), (0., .5))
    hint = add(bp, unreal.TextBlock, 'ScanHint', canvas)
    hint.widget.set_text(unreal.Text('1 切换仪器 · 2 装备枪\n按住 Q 一秒扫描'))
    hint.widget.set_font_size(20)
    hint.widget.set_editor_property('justification', unreal.TextJustify.CENTER)
    hint.widget.set_shadow_offset(unreal.Vector2D(1., 1.))
    hint.widget.set_shadow_color_and_opacity(unreal.LinearColor(0., 0., 0., 1.))
    slot(hint, (.5, 1.), (0., -28.), (780., 64.), (.5, 1.))
    progress = add(bp, unreal.ProgressBar, 'ScanProgress', canvas)
    progress.widget.set_percent(0.)
    progress.widget.set_fill_color_and_opacity(unreal.LinearColor(.2, .85, .6, 1.))
    progress.widget.set_visibility(unreal.SlateVisibility.COLLAPSED)
    slot(progress, (.5, .5), (0., 92.), (220., 10.), (.5, 0.))
    for item in (summary, hint, progress):
        UMG.call_method('ToggleWidgetAsVariable', (bp, item.widget, True))
    assert UMG.call_method('CompileWidgetBlueprint', (bp,))
    save(bp)
    return bp


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    backed_up = backup()
    ui = panel()
    scanner = ASSETS.load_asset(SCANNER) if ASSETS.does_asset_exist(SCANNER) else None
    if scanner is None:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.AnomalyScannerComponent.static_class())
        scanner = unreal.AssetToolsHelpers.get_asset_tools().create_asset('BPC_Scanner', '/Game/Core/Components', unreal.Blueprint, factory)
    assert scanner
    save(scanner)
    defaults = unreal.get_default_object(scanner.generated_class())
    defaults.set_editor_property('panel_class', ui.generated_class())
    defaults.set_editor_property('scan_range', 300.)
    defaults.set_editor_property('scan_duration', 1.)
    assert ASSETS.save_loaded_asset(scanner, only_if_is_dirty=False)
    player = ASSETS.load_asset(PLAYER)
    assert player
    components = ActorTools.get_components(unreal.get_default_object(player.generated_class()))
    existing = [c for c in components if isinstance(c, unreal.AnomalyScannerComponent)]
    assert len(existing) <= 1
    if not existing:
        ActorTools.add_component(player, scanner.generated_class(), 'T12Scanner')
    save(player)
    components = ActorTools.get_components(unreal.get_default_object(player.generated_class()))
    actual = [c for c in components if isinstance(c, unreal.AnomalyScannerComponent)]
    assert len(actual) == 1
    actual[0].set_editor_property('panel_class', ui.generated_class())
    actual[0].set_editor_property('scan_range', 300.)
    actual[0].set_editor_property('scan_duration', 1.)
    assert ASSETS.save_loaded_asset(player, only_if_is_dirty=False)
    report = dict(status='BUILT', backup=str(backed_up), assets=[PLAYER, SCANNER, PANEL],
                  component=actual[0].get_name(), gameplay_tested=False,
                  scope='T12 only; no PIE, MCP, screen automation or packaging')
    (OUT / 'build_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('[T12] BUILD PASS')


main()
