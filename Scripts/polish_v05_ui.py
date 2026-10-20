"""T41 UI/terminal clarity, allowlisted v0.5 assets and new Lab only."""
import json,hashlib
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
ROOT=Path(__file__).resolve().parents[1]
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);U=unreal.get_default_object(unreal.UMGToolSet)
old=[r for r in json.loads((ROOT/'Saved/V05/T33/source_copy_manifest.json').read_text(encoding='utf-8'))['files'] if r['path'].startswith('Content/')]
assert all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in old)
menu=A.load_asset('/Game/Prototype/V05/UI/WBP_MainMenu_V05');assert menu
widgets={str(x.widget.get_name()):x.widget for x in U.call_method('GetWidgets',(menu,)).widgets if x.widget}
values={'GuideKey0':'WASD / 鼠标 / 空格','GuideAction0':'移动、观察、跳跃；基地始终安全',
'GuideKey1':'基地 E / ↑↓ / ENTER','GuideAction1':'查看终端、选择商品、购买/确认出发',
'GuideKey2':'实验室 E','GuideAction2':'开箱、拾取；气闸确认撤离',
'GuideKey3':'按住 Q','GuideAction3':'默认1秒；B断电较慢，缓存免费',
'GuideKey4':'1 / 2 / F','GuideAction4':'切换装备；决策继续/返程；放诱饵',
'GuideKey5':'ESC','GuideAction5':'关闭基地面板；成功/死亡自动回基地',
'GuideRule':'每轮三箱选一；B配电有取舍，C舱对观察者无效。\n成功撤离保存收益；死亡或退出丢失携带物品。'}
for name,text in values.items():assert name in widgets;widgets[name].set_text(unreal.Text(text))
widgets['GuideRule'].slot.set_size(unreal.Vector2D(680,64))
BlueprintTools.compile_blueprint(menu,warnings_as_errors=True);assert A.save_loaded_asset(menu,only_if_is_dirty=False)
assert L.load_level('/Game/Maps/L_Lab')
for actor in E.get_all_level_actors():
    if isinstance(actor,unreal.AnomalyEnvironmentTerminal):
        yaw=90 if actor.get_editor_property('Kind')==unreal.AnomalyEnvironmentKind.POWER else -90
        actor.set_actor_rotation(unreal.Rotator(pitch=0,yaw=yaw,roll=0),False)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
tiles=unreal.AnomalyRoundCoordinator.build_exploration_navigation(world);assert tiles>0;assert L.save_current_level()
assert all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in old)
out=ROOT/'Saved/V05/T41';out.mkdir(parents=True,exist_ok=True)
(out/'ui_polish.json').write_text(json.dumps(dict(status='PASS',guide_fields=len(values),terminal_fronts_corrected=2,nav_tiles=tiles,protected_content=len(old)),indent=2),encoding='utf-8')
unreal.log('[T41 UI] PASS')
