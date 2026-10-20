"""Independent reload/compile audit only. Does not start gameplay or PIE."""
import json
from pathlib import Path
import unreal
from editor_toolset.toolsets.actor import ActorTools
from editor_toolset.toolsets.blueprint import BlueprintTools

ROOT = Path(__file__).resolve().parent.parent
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
paths = ['/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter',
         '/Game/Core/Components/BPC_Scanner', '/Game/UI/WBP_ScanPanel',
         '/Game/Anomalies/Containers/BP_AnomalyBox']
assets = [ASSETS.load_asset(path) for path in paths]
for bp in assets:
    assert bp
    BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)
components = ActorTools.get_components(unreal.get_default_object(assets[0].generated_class()))
scanners = [c for c in components if isinstance(c, unreal.AnomalyScannerComponent)]
equipment = [c for c in components if isinstance(c, unreal.AnomalyEquipmentComponent)]
assert len(scanners) == len(equipment) == 1
for component in (scanners[0], unreal.get_default_object(assets[1].generated_class())):
    assert component.get_editor_property('scan_range') == 300.
    assert component.get_editor_property('scan_duration') == 1.
    assert component.get_editor_property('panel_class') == assets[2].generated_class()
for prop in ('metal_detector_mesh', 'bio_detector_mesh', 'matter_analyzer_mesh', 'gun_mesh'):
    assert equipment[0].get_editor_property(prop), prop
umg = unreal.get_default_object(unreal.UMGToolSet)
widgets = {item.widget.get_name(): item.widget.get_class().get_name()
           for item in umg.call_method('GetWidgets', (assets[2],)).widgets}
assert widgets['ScanSummary'] == widgets['ScanHint'] == 'TextBlock'
assert widgets['ScanProgress'] == 'ProgressBar'
report = dict(status='PASS', scope='Independent asset reload and compile only',
              assets=paths, scanner=scanners[0].get_name(), widgets=widgets,
              gameplay_tested=False, visual_tested=False)
(ROOT / 'Saved/T12/reload_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('[T12] RELOAD PASS')
