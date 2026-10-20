"""Build T15 health/status assets and update player, spider and spawner defaults.

Run through cpp_migration.py editor after native Editor compilation. No MCP or PIE.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import unreal
from editor_toolset.toolsets.actor import ActorTools
from editor_toolset.toolsets.blueprint import BlueprintTools

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Saved/T15'
PLAYER = '/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter'
SPIDER = '/Game/Anomalies/Creatures/BP_Spider'
SPAWNER = '/Game/Anomalies/Containers/BP_BoxSpawner'
HEALTH = '/Game/Core/Components/BPC_Health'
STATUS = '/Game/UI/WBP_HealthThreat'
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
UMG = unreal.get_default_object(unreal.UMGToolSet)


def save(asset):
    BlueprintTools.compile_blueprint(asset, warnings_as_errors=True)
    assert ASSETS.save_loaded_asset(asset, only_if_is_dirty=False), asset.get_path_name()


def backup():
    folder = OUT / ('AssetBackup_' + datetime.now().strftime('%Y%m%dT%H%M%S%f'))
    folder.mkdir(parents=True)
    for path in (PLAYER, SPIDER, SPAWNER, HEALTH, STATUS):
        source = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
        if not source.is_file():
            assert path in (HEALTH, STATUS), source
            continue
        target = folder / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return folder


def add_text(widget, canvas, name, content, font_size, color, anchor, position, size, align):
    item = UMG.call_method('AddWidget', (widget, unreal.TextBlock.static_class(), name, canvas, -1))
    assert item.widget, name
    item.widget.set_text(unreal.Text(content))
    item.widget.set_font_size(font_size)
    item.widget.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(*color)))
    item.widget.set_shadow_offset(unreal.Vector2D(2., 2.))
    item.widget.set_shadow_color_and_opacity(unreal.LinearColor(0., 0., 0., 1.))
    item.slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(*anchor), maximum=unreal.Vector2D(*anchor)))
    item.slot.set_position(unreal.Vector2D(*position))
    item.slot.set_size(unreal.Vector2D(*size))
    item.slot.set_alignment(unreal.Vector2D(*align))
    UMG.call_method('ToggleWidgetAsVariable', (widget, item.widget, True))
    return item.widget


def make_status():
    widget = ASSETS.load_asset(STATUS) if ASSETS.does_asset_exist(STATUS) else None
    if widget is None:
        widget = UMG.call_method('CreateWidgetBlueprint', ('/Game/UI', 'WBP_HealthThreat', unreal.AnomalyStatusWidget.static_class()))
    assert widget
    old = UMG.call_method('GetWidgets', (widget,)).widgets
    if old:
        assert UMG.call_method('RemoveWidget', (widget, old[0].widget))
    canvas = UMG.call_method('AddWidget', (widget, unreal.CanvasPanel.static_class(), 'StatusCanvas', None, -1)).widget
    assert canvas
    add_text(widget, canvas, 'HPText', 'HP  100 / 100', 24, (.88, .95, .92, 1.),
             (0., 0.), (26., 115.), (270., 40.), (0., 0.))
    warning = add_text(widget, canvas, 'ThreatText', '危险：收容失效', 30, (1., .28, .22, 1.),
                       (.5, 0.), (0., 30.), (800., 65.), (.5, 0.))
    warning.set_editor_property('justification', unreal.TextJustify.CENTER)
    warning.set_visibility(unreal.SlateVisibility.COLLAPSED)
    damage = add_text(widget, canvas, 'DamageText', '受伤  -25', 30, (1., .18, .18, 1.),
                      (.5, .5), (0., -110.), (420., 60.), (.5, .5))
    damage.set_editor_property('justification', unreal.TextJustify.CENTER)
    damage.set_visibility(unreal.SlateVisibility.COLLAPSED)
    assert UMG.call_method('CompileWidgetBlueprint', (widget,))
    save(widget)
    return widget


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    previous = backup()
    status = make_status()
    health = ASSETS.load_asset(HEALTH) if ASSETS.does_asset_exist(HEALTH) else None
    if health is None:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.AnomalyHealthComponent.static_class())
        health = unreal.AssetToolsHelpers.get_asset_tools().create_asset('BPC_Health', '/Game/Core/Components', unreal.Blueprint, factory)
    assert health
    save(health)
    settings = dict(max_health=100, threat_damage=25, damage_cooldown=1.5,
                    status_widget_class=status.generated_class())
    health_defaults = unreal.get_default_object(health.generated_class())
    for key, value in settings.items():
        health_defaults.set_editor_property(key, value)
    assert ASSETS.save_loaded_asset(health, only_if_is_dirty=False)

    player = ASSETS.load_asset(PLAYER)
    assert player
    components = ActorTools.get_components(unreal.get_default_object(player.generated_class()))
    existing = [component for component in components if isinstance(component, unreal.AnomalyHealthComponent)]
    assert len(existing) <= 1
    if not existing:
        ActorTools.add_component(player, health.generated_class(), 'T15Health')
    save(player)
    components = ActorTools.get_components(unreal.get_default_object(player.generated_class()))
    actual = [component for component in components if isinstance(component, unreal.AnomalyHealthComponent)]
    assert len(actual) == 1
    for key, value in settings.items():
        actual[0].set_editor_property(key, value)
    assert ASSETS.save_loaded_asset(player, only_if_is_dirty=False)

    spider = ASSETS.load_asset(SPIDER)
    spawner = ASSETS.load_asset(SPAWNER)
    assert spider and spawner
    save(spider)
    spider_defaults = unreal.get_default_object(spider.generated_class())
    for key, value in dict(move_speed=330., max_health=100, auto_resolve_delay=20.,
                           attack_radius=80., auto_resolve_threat=True).items():
        spider_defaults.set_editor_property(key, value)
    assert ASSETS.save_loaded_asset(spider, only_if_is_dirty=False)
    save(spawner)
    coordinator = unreal.get_default_object(spawner.generated_class())
    for key, value in dict(threat_warning_seconds=1., threat_survival_seconds=20.,
                           containment_message_seconds=1., threat_spawn_retry_delay=1.,
                           max_threat_spawn_retries=3).items():
        coordinator.set_editor_property(key, value)
    assert ASSETS.save_loaded_asset(spawner, only_if_is_dirty=False)
    report = dict(status='BUILT', backup=str(previous), assets=[PLAYER, SPIDER, SPAWNER, HEALTH, STATUS],
                  health_component=actual[0].get_name(), gameplay_tested=False,
                  scope='T15 Python/C++ build; no MCP, screen automation, PIE or package')
    (OUT / 'build_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('[T15] BUILD PASS')


main()
