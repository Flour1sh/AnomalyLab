"""Independent T14 asset reload and compile only; does not run a round."""
import json
from pathlib import Path

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools

ROOT = Path(__file__).resolve().parent.parent
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
spawner = ASSETS.load_asset('/Game/Anomalies/Containers/BP_BoxSpawner')
widget = ASSETS.load_asset('/Game/UI/WBP_RoundDecision')
player = ASSETS.load_asset('/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter')
assert spawner and widget and player
for asset in (widget, spawner, player):
    BlueprintTools.compile_blueprint(asset, warnings_as_errors=True)
defaults = unreal.get_default_object(spawner.generated_class())
assert isinstance(defaults, unreal.AnomalyRoundCoordinator)
assert defaults.get_editor_property('decision_widget_class') == widget.generated_class()
assert abs(defaults.get_editor_property('next_round_delay') - 2.0) < 1.e-6
widgets = {item.widget.get_name() for item in unreal.get_default_object(unreal.UMGToolSet).call_method('GetWidgets', (widget,)).widgets}
assert 'StatusText' in widgets
report = dict(status='PASS', assets=[spawner.get_path_name(), widget.get_path_name(), player.get_path_name()],
              widget_bindings=sorted(widgets), reward_delay=2.0, gameplay_tested=False,
              scope='Independent asset reload and Blueprint compile only')
(ROOT / 'Saved/T14/reload_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('[T14] RELOAD PASS')
