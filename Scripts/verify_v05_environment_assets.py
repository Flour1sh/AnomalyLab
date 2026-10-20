import json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[1]
L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert L.load_level('/Game/Maps/L_Lab')
actors=E.get_all_level_actors();services=[x for x in actors if isinstance(x,unreal.AnomalyEnvironmentController)]
terminals=[x for x in actors if isinstance(x,unreal.AnomalyEnvironmentTerminal)];assert len(services)==1 and terminals
config=services[0].get_editor_property('Config');assert config and config.get_path_name()=='/Game/Prototype/V05/Data/DA_Environment.DA_Environment'
assert config.get_editor_property('PowerScanMultiplier')==1.75 and config.get_editor_property('PowerObserveMultiplier')==1.5
assert any(t.get_editor_property('Kind')==unreal.AnomalyEnvironmentKind.POWER for t in terminals)
assert L.load_level('/Game/Maps/L_Hub')
assert not any(isinstance(x,(unreal.AnomalyEnvironmentController,unreal.AnomalyEnvironmentTerminal)) for x in E.get_all_level_actors())
phase=json.loads((ROOT/'Saved/CppMigration/latest.json').read_text(encoding='utf-8')).get('asset_phase','T38')
task=phase[:3] if phase[:3] in ['T38','T39','T40','T41','T42'] else 'T38'
if task!='T38':
    assert config.get_editor_property('enable_chamber') and len(terminals)==2
if task in ['T40','T41','T42']:
    assert config.get_editor_property('enable_events') and config.get_editor_property('MaxEvents')==2
out=ROOT/'Saved/V05'/task;out.mkdir(parents=True,exist_ok=True)
(out/'environment_reload.json').write_text(json.dumps(dict(status='PASS',fresh_process=True,lab_actors=len(actors),services=1,terminals=len(terminals),hub_environment_actors=0),indent=2),encoding='utf-8')
unreal.log('[ENV RELOAD] PASS')
