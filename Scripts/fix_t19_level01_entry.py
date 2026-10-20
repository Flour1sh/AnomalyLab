"""Back up and correct only Level01 PlayerStart's pre-existing downward rotation."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal

root = Path(__file__).resolve().parent.parent
out = root / 'Saved/T19Menu'
relative = str(Path('Content/Prototype/Maps/L_Prototype.umap'))
path = root / relative
report_path = out / 'entry_fix_report.json'
current_hash = hashlib.sha256(path.read_bytes()).hexdigest()
if report_path.exists():
    previous = json.loads(report_path.read_text(encoding='utf-8'))
    assert current_hash == previous['after_sha256'], 'Level01 changed since entry fix; audit before rerunning'
    unreal.log('[T19Menu] ENTRY ALREADY FIXED')
else:
    baseline = json.loads((out / 'gameplay_baseline_hashes.json').read_text(encoding='utf-8'))
    assert current_hash == baseline[relative], 'Unexpected Level01 changes since baseline'
    backup = out / ('Level01EntryBefore_' + datetime.now().strftime('%Y%m%dT%H%M%S')) / 'L_Prototype.umap'
    backup.parent.mkdir(parents=True)
    shutil.copy2(path, backup)
    level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    assert level.load_level('/Game/Prototype/Maps/L_Prototype')
    starts = [actor for actor in actors.get_all_level_actors() if isinstance(actor, unreal.PlayerStart)]
    assert len(starts) == 1
    start = starts[0]
    old = start.get_actor_rotation()
    assert abs(old.pitch + 90) < .01 and abs(old.yaw) < .01, str(old)
    before = dict(pitch=old.pitch, yaw=old.yaw, roll=old.roll)
    assert start.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), False)
    assert level.save_current_level()
    new = start.get_actor_rotation()
    report = dict(status='PASS', map=relative, before_sha256=current_hash,
                  after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), backup=str(backup),
                  before_rotation=before, after_rotation=dict(pitch=new.pitch, yaw=new.yaw, roll=new.roll),
                  reason='Existing PlayerStart points straight down. Correct initial Level01 view after main-menu start; no gameplay rules changed.')
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('[T19Menu] ENTRY FIX PASS')
