"""Read-only snapshot of the currently open editor. Invoked via UE MCP console."""
import json
from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir()).resolve()
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=editor.get_editor_world()
box_class=unreal.load_class(None,'/Game/Anomalies/Containers/BP_AnomalyBox.BP_AnomalyBox_C')
spider_class=unreal.load_class(None,'/Game/Anomalies/Creatures/BP_Spider.BP_Spider_C')
boxes=list(unreal.GameplayStatics.get_all_actors_of_class(world,box_class))
data={'world':world.get_path_name(),'pie_active':editor.get_game_world() is not None,'boxes':[],
      'placed_spider_count':len(unreal.GameplayStatics.get_all_actors_of_class(world,spider_class))}
for box in boxes:
    point=next(c for c in box.get_components_by_class(unreal.SceneComponent) if c.get_name()=='CreatureSpawnPoint')
    data['boxes'].append({'actor':box.get_path_name(),'location':str(box.get_actor_location()),
                         'spawn_point':str(point.get_world_location()),'forced':box.get_editor_property('bForceOutcome'),
                         'threat_class':str(box.get_editor_property('ThreatClass'))})
(root/'Saved/T05/live_preflight.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[T05PIE] Live preflight '+json.dumps(data,ensure_ascii=False))
