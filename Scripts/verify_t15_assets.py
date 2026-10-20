"""Independent T15 asset reload and compile; no gameplay."""
import json
from pathlib import Path

import unreal
from editor_toolset.toolsets.actor import ActorTools
from editor_toolset.toolsets.blueprint import BlueprintTools

ROOT = Path(__file__).resolve().parent.parent
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
paths = ['/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter',
         '/Game/Anomalies/Creatures/BP_Spider',
         '/Game/Anomalies/Containers/BP_BoxSpawner',
         '/Game/Core/Components/BPC_Health', '/Game/UI/WBP_HealthThreat']
player, spider, spawner, health, status = [ASSETS.load_asset(path) for path in paths]
for asset in (status, health, player, spider, spawner):
    assert asset
    BlueprintTools.compile_blueprint(asset, warnings_as_errors=True)
components = ActorTools.get_components(unreal.get_default_object(player.generated_class()))
health_components = [component for component in components if isinstance(component, unreal.AnomalyHealthComponent)]
assert len(health_components) == 1
for component in (health_components[0], unreal.get_default_object(health.generated_class())):
    assert component.get_editor_property('max_health') == 100
    assert component.get_editor_property('threat_damage') == 25
    assert abs(component.get_editor_property('damage_cooldown') - 1.5) < 1.e-6
    assert component.get_editor_property('status_widget_class') == status.generated_class()
enemy = unreal.get_default_object(spider.generated_class())
assert enemy.get_editor_property('move_speed') == 330.
assert enemy.get_editor_property('auto_resolve_delay') == 20.
assert enemy.get_editor_property('attack_radius') == 80.
assert enemy.get_editor_property('max_health') == 100
coordinator = unreal.get_default_object(spawner.generated_class())
assert coordinator.get_editor_property('threat_warning_seconds') == 1.
assert coordinator.get_editor_property('threat_survival_seconds') == 20.
assert coordinator.get_editor_property('max_threat_spawn_retries') == 3
widgets = {item.widget.get_name() for item in unreal.get_default_object(unreal.UMGToolSet).call_method('GetWidgets', (status,)).widgets}
assert {'HPText', 'ThreatText', 'DamageText'} <= widgets
report = dict(status='PASS', assets=paths, health_component=health_components[0].get_name(),
              widgets=sorted(widgets), gameplay_tested=False,
              scope='Independent reload/compile only; no MCP, PIE, screen automation or package')
(ROOT / 'Saved/T15/reload_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('[T15] RELOAD PASS')
