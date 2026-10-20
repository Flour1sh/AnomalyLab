"""Reload menu assets and inspect the original level without saving gameplay assets."""
import hashlib
import json
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools

root = Path(__file__).resolve().parent.parent
out = root / 'Saved/T19Menu'
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
checks = []


def check(name, passed):
    checks.append(dict(check=name, passed=bool(passed)))
    assert passed, name


widget = assets.load_asset('/Game/UI/Menu/WBP_MainMenu')
check('Menu widget loads', widget is not None)
BlueprintTools.compile_blueprint(widget, warnings_as_errors=True)
defaults = unreal.get_default_object(widget.generated_class())
check('Menu sounds referenced', defaults.get_editor_property('hover_sound') and defaults.get_editor_property('select_sound'))
tree = unreal.get_default_object(unreal.UMGToolSet).call_method('GetWidgets', (widget,)).widgets
names = [item.widget.get_name() for item in tree]
check('No duplicate widget names', len(names) == len(set(names)))
check('All four main buttons exist', all(name in names for name in ('StartButton', 'SettingsButton', 'GuideButton', 'QuitButton')))
check('All modal panels exist', all(name in names for name in ('SettingsPanel', 'GuidePanel', 'QuitPanel', 'LoadingPanel')))
check('Responsive ScaleBox exists', 'ResponsiveFrame' in names)

check('Menu map reloads', level.load_level('/Game/Prototype/Maps/L_MainMenu'))
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
check('Menu map overrides gameplay GameMode', world.get_world_settings().get_editor_property('default_game_mode') == unreal.AnomalyMenuGameMode.static_class())
menu_actors = list(actors.get_all_level_actors())
labels = [actor.get_actor_label() for actor in menu_actors]
check('No duplicate menu actor labels', len(labels) == len(set(labels)))
check('No gameplay coordinator in menu', not any(isinstance(actor, unreal.AnomalyRoundCoordinator) for actor in menu_actors))
check('One tagged menu camera', sum(isinstance(actor, unreal.CameraActor) and actor.actor_has_tag('MenuCamera') for actor in menu_actors) == 1)
check('Three decorative crates', sum(name.startswith('MENU_StaticCrate_') for name in labels) == 3)
check('Menu room tone present', labels.count('MENU_RoomTone') == 1)

check('Level01 reloads', level.load_level('/Game/Prototype/Maps/L_Prototype'))
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
check('Level01 keeps Blueprint GameMode', 'BP_FirstPersonGameMode' in world.get_world_settings().get_editor_property('default_game_mode').get_path_name())
spawns = [dict(label=actor.get_actor_label(), location=str(actor.get_actor_location()), rotation=str(actor.get_actor_rotation()))
          for actor in actors.get_all_level_actors() if isinstance(actor, unreal.PlayerStart)]
check('Level01 keeps coordinator', sum(isinstance(actor, unreal.AnomalyRoundCoordinator) for actor in actors.get_all_level_actors()) == 1)
baseline = json.loads((out / 'gameplay_baseline_hashes.json').read_text(encoding='utf-8'))
entry_fix = json.loads((out / 'entry_fix_report.json').read_text(encoding='utf-8')) if (out / 'entry_fix_report.json').is_file() else None
for path, expected in baseline.items():
    if entry_fix and path == entry_fix['map']:
        check('Level01 matches documented PlayerStart-only correction', hashlib.sha256((root / path).read_bytes()).hexdigest() == entry_fix['after_sha256'])
    else:
        check('Gameplay asset unchanged: ' + path, hashlib.sha256((root / path).read_bytes()).hexdigest() == expected)
report = dict(status='PASS', checks=checks, menu_actor_count=len(menu_actors), widget_count=len(names), level01_player_starts=spawns,
              scope='Asset reload, compile, saved menu structure and gameplay asset hashes; no gameplay assets saved')
(out / 'reload_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('[T19Menu] RELOAD PASS')
