"""D3D12 render-target photographs of the saved level; no viewport/screen capture."""
from pathlib import Path
import json
from datetime import datetime
import unreal
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'Saved/ScenePolish'/('Views_'+datetime.now().strftime('%Y%m%dT%H%M%S'));OUT.mkdir(parents=True,exist_ok=False)
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert L.load_level('/Game/Prototype/Maps/L_Prototype')
materials=[]
for folder in ['/Game/Prototype/Environment/ScenePolish','/Game/Prototype/Environment/T20','/Game/Prototype/Data/Items']:
    for path in A.list_assets(folder,recursive=True,include_folder=False):
        o=A.load_asset(path)
        if isinstance(o,unreal.Material):
            unreal.MaterialEditingLibrary.recompile_material(o);materials.append(o)
unreal.AnomalyRoundCoordinator.finish_asset_compilation()
for m in materials:
    if '/ScenePolish/' in m.get_path_name():assert A.save_loaded_asset(m,only_if_is_dirty=False)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
o=E.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector(),unreal.Rotator(),transient=True)
c=o.get_component_by_class(unreal.SceneCaptureComponent2D)
c.set_editor_property('capture_every_frame',False)
c.set_editor_property('capture_on_movement',False)
c.set_editor_property('always_persist_rendering_state',True)
c.set_editor_property('capture_source',unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
c.set_editor_property('fov_angle',88.)
rt=unreal.RenderingLibrary.create_render_target2d(world,1600,900,unreal.TextureRenderTargetFormat.RTF_RGBA8)
c.set_editor_property('texture_target',rt)
views=[('01_entry',(300,1150,175),(-60,1840,145)),('02_hall',(0,790,180),(0,-600,170)),
       ('03_analysis',(-410,-240,175),(-1100,420,140)),('04_power',(410,-240,175),(1090,420,140)),
       ('05_containment',(370,-610,175),(-60,-1310,140))]
for name,xyz,target in views:
    o.set_actor_location(unreal.Vector(*xyz),False,False)
    o.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*xyz),unreal.Vector(*target)),False)
    for i in range(8):
        c.capture_scene()
        unreal.RenderingLibrary.export_render_target(world,rt,str(OUT),name+'.png')
    assert (OUT/(name+'.png')).is_file(),name
E.destroy_actor(o)
(ROOT/'Saved/ScenePolish/capture_report.json').write_text(json.dumps(dict(status='PASS',scope='Actual D3D12 SceneCapture render targets, saved level; no game pawn/HUD and no human operation',directory=str(OUT),views=[v[0] for v in views],materials_warmed=len(materials)),indent=2),encoding='utf-8')
unreal.log('[SCENE POLISH] CAPTURE PASS')
