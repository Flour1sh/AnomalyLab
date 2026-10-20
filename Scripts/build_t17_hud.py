"""Translate legacy HUD output and consolidate the v0.2 overlay layout."""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools

root = Path(__file__).resolve().parent.parent
out = root / 'Saved/T17'
out.mkdir(parents=True, exist_ok=True)
backup = out / ('AssetBackup_' + datetime.now().strftime('%Y%m%dT%H%M%S%f'))
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
umg = unreal.get_default_object(unreal.UMGToolSet)
paths = ['/Game/UI/WBP_PrototypeHUD', '/Game/UI/WBP_ScanPanel',
         '/Game/UI/WBP_HealthThreat', '/Game/UI/WBP_RoundDecision']
for path in paths:
    source = root / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    target = backup / source.relative_to(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def widgets(bp):
    return {item.widget.get_name(): item.widget for item in umg.call_method('GetWidgets', (bp,)).widgets}


def text(widget, value):
    widget.set_text(unreal.Text(value))


def layout(widget, anchor, position, size, alignment, font_size=None):
    slot = widget.slot
    slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(*anchor), maximum=unreal.Vector2D(*anchor)))
    slot.set_position(unreal.Vector2D(*position))
    slot.set_size(unreal.Vector2D(*size))
    slot.set_alignment(unreal.Vector2D(*alignment))
    if font_size is not None:
        widget.set_font_size(font_size)


hud = assets.load_asset(paths[0])
assert hud
w = widgets(hud)
for name, value in {'MoneyText': '收益：$0', 'ThreatText': '成功收容：0 / 2',
                    'InteractionPrompt': '[E] 开箱', 'ResultText': '高价值 +$0'}.items():
    text(w[name], value)
layout(w['MoneyText'], (0., 0.), (26., 26.), (420., 42.), (0., 0.))
layout(w['ThreatText'], (0., 0.), (26., 69.), (390., 36.), (0., 0.))

replacements = {
    'Money: ${Money}': '收益：${Money}',
    'TRASH +$3': '废品 +$3',
    'WARNING': '危险：收容失效',
    'HIGH VALUE +${Amount}': '高价值 +${Amount}',
    'SPIDER ATTACKED': '遭受袭击',
    'PROTOTYPE ERROR\nPress R to Restart': '原型运行异常\n按 R 重新开始',
    'RUN OVER\nFinal Money: $': '行动结束\n带出金额：$',
    '\nThreats: ': '\n成功收容：',
    '\nPress R to Restart': '\n按 R 重新开始',
    'Threats: ': '成功收容：',
}
changed = {}
for graph in BlueprintTools.list_graphs(hud):
    for node in BlueprintTools.find_nodes(graph):
        for pin in unreal.BlueprintEditorLibrary.list_input_pins(node):
            raw = str(pin.get_pin_value())
            for old, new in replacements.items():
                if old in raw:
                    assert pin.set_pin_value(new), (graph.get_name(), node.get_name(), old)
                    changed[old] = changed.get(old, 0) + 1
                    break
assert all(value > 0 for value in changed.values())
assert set(changed) == set(replacements), set(replacements) - set(changed)
BlueprintTools.compile_blueprint(hud, warnings_as_errors=True)
assert assets.save_loaded_asset(hud, only_if_is_dirty=False)

scan = assets.load_asset(paths[1]); status = assets.load_asset(paths[2]); decision = assets.load_asset(paths[3])
assert scan and status and decision
sw, hw, dw = widgets(scan), widgets(status), widgets(decision)
text(sw['ScanSummary'], '当前箱子 · 扫描记录\n\n高价值金额：未扫描\n威胁可能性：未扫描\n高价值可能性：未扫描')
text(sw['ScanHint'], '1 切换仪器 · 2 装备枪\n按住 Q 一秒扫描')
layout(sw['ScanSummary'], (0., .5), (26., 0.), (410., 370.), (0., .5), 19)
layout(sw['ScanHint'], (.5, 1.), (0., -24.), (760., 62.), (.5, 1.), 19)
text(hw['ThreatText'], '危险：收容失效')
text(hw['DamageText'], '受伤  -25')
layout(hw['HPText'], (0., 0.), (26., 112.), (280., 40.), (0., 0.))
layout(hw['ThreatText'], (.5, 0.), (0., 124.), (600., 58.), (.5, 0.), 26)
layout(hw['DamageText'], (.5, .5), (0., -100.), (420., 60.), (.5, .5), 28)
text(dw['StatusText'], '当前收益  $0\n完成回合  0    成功收容  0\n\n[1] 继续    [2] 撤离')
layout(dw['StatusText'], (.5, .5), (0., 0.), (900., 340.), (.5, .5), 29)
for bp in (scan, status, decision):
    BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)
    assert assets.save_loaded_asset(bp, only_if_is_dirty=False)

report = {'status': 'BUILT', 'backup': str(backup), 'assets': paths,
          'graph_replacements': changed, 'reference_resolutions': [[1280, 720], [1920, 1080]],
          'scope': 'Widget anchors/text and legacy graph strings; runtime and raster validation follow'}
(out / 'build_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('[T17] BUILD PASS')
