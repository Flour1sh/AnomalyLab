"""Minimal existing-menu text update; preserve every button, panel and input binding."""
import json,shutil,hashlib
from pathlib import Path
from datetime import datetime
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Saved/V04/T32'/('Menu_'+datetime.now().strftime('%Y%m%dT%H%M%S%f'));OUT.mkdir(parents=True)
target='Content/UI/Menu/WBP_MainMenu.uasset';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'Content').rglob('*') if p.is_file() and p.relative_to(ROOT).as_posix()!=target}
shutil.copy2(ROOT/target,OUT/'WBP_MainMenu.uasset')
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);U=unreal.get_default_object(unreal.UMGToolSet);bp=A.load_asset('/Game/UI/Menu/WBP_MainMenu')
w={str(x.widget.get_name()):x.widget for x in U.call_method('GetWidgets',(bp,)).widgets if x.widget}
values={'Version':'v0.4 RC   /   ANOMALY LAB','GuideAction0':'移动 / 观察；空格跳跃','GuideKey1':'↑↓ / ENTER / F','GuideAction1':'局外选择 / 购买 / 局内放诱饵',
 'GuideAction2':'开箱 / 拾取 / 入口确认撤离','GuideAction3':'扫描1秒；默认3次/种，缓存免费','GuideAction4':'切仪器/枪；决策时继续/返程',
 'GuideAction5':'终局重开；永久余额与升级保留','GuideRule':'背包4→5格；入口E兑现，死亡丢携货。\n观察者正视停步，红眼保持距离；诱饵无效。'}
for name,text in values.items():w[name].set_text(unreal.Text(text))
w['GuideRule'].slot.set_size(unreal.Vector2D(680,56))
BlueprintTools.compile_blueprint(bp,warnings_as_errors=True);assert A.save_loaded_asset(bp,only_if_is_dirty=False);unreal.AnomalyRoundCoordinator.finish_asset_compilation()
assert all(sha(ROOT/rel)==digest for rel,digest in protected.items()),'Unrelated Content changed'
(OUT/'report.json').write_text(json.dumps(dict(status='PASS',values=values,protected_files=len(protected)),ensure_ascii=False,indent=2),encoding='utf-8')
