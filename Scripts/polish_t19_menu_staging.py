"""Ground the three menu-only display crates using their actual mesh bounds."""
import json
from pathlib import Path
import unreal

root = Path(__file__).resolve().parent.parent
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert level.load_level('/Game/Prototype/Maps/L_MainMenu')
items = {actor.get_actor_label(): actor for actor in actors.get_all_level_actors()}
adjustments = []
for i in range(3):
    crate = items['MENU_StaticCrate_%d' % i]
    support = items['PROTOTYPE_CentralPedestal' if i == 0 else 'ENV_SM_Floor']
    support_origin, support_extent = support.get_actor_bounds(False)
    crate_origin, crate_extent = crate.get_actor_bounds(False)
    offset = support_origin.z + support_extent.z - (crate_origin.z - crate_extent.z)
    location = crate.get_actor_location()
    location.z += offset
    crate.set_actor_location(location, False, False)
    adjustments.append(dict(actor=crate.get_actor_label(), height_offset=offset))
assert level.save_current_level()
(root / 'Saved/T19Menu/staging_report.json').write_text(json.dumps(dict(status='PASS', adjustments=adjustments), indent=2), encoding='utf-8')
unreal.log('[T19Menu] STAGING PASS')
