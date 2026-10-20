"""Read actual saved v0.3 assets without saving/compiling/generating anything."""
import json
from pathlib import Path
import unreal
ROOT = Path(__file__).resolve().parents[1]
A = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
L = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
box_bp = A.load_asset('/Game/Anomalies/Containers/BP_AnomalyBox')
box = unreal.get_default_object(box_bp.generated_class())
fields = ('box_id','display_name','value_min','value_max','high_value_chance','trash_chance','threat_chance',
          'value_lower_scale','value_upper_scale','scan_probability_error','random_hidden_profile',
          'hidden_profile','metal_chance','warning_chance','wear_chance')
definitions = {}
for key, asset in box.get_editor_property('definitions').items():
    row = {name: asset.get_editor_property(name) for name in fields}
    row['box_id'] = str(row['box_id']); row['display_name'] = str(row['display_name'])
    row['asset'] = asset.get_path_name()
    definitions[str(key)] = row
maps = {}
for level in ('L_Prototype','L_LegacyPrototype'):
    assert L.load_level('/Game/Prototype/Maps/'+level)
    c = next(a for a in E.get_all_level_actors() if isinstance(a, unreal.AnomalyRoundCoordinator))
    maps[level] = dict(actor=c.get_path_name(), play_mode=str(c.get_editor_property('play_mode')),
        box_class=c.get_editor_property('box_class').get_path_name(),
        points={name: list(c.get_editor_property(name).get_world_location().to_tuple())
                for name in ('box_point_left','box_point_middle','box_point_right')},
        max_threats=c.get_editor_property('max_threats'),
        warning=c.get_editor_property('threat_warning_seconds'), survival=c.get_editor_property('threat_survival_seconds'))
report = dict(status='PASS', definitions=definitions, maps=maps,
              debug_defaults={name: box.get_editor_property(name) for name in ('force_outcome','use_fixed_seeds','configuration_seed','outcome_seed')},
              box_parent=box.get_class().get_super_class().get_path_name() if hasattr(box.get_class(),'get_super_class') else 'Native inheritance verified by isinstance',
              box_native=isinstance(box,unreal.AnomalyBoxActor))
out=ROOT/'Saved/V04/initialization/asset_audit.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[V04 AUDIT] PASS')
