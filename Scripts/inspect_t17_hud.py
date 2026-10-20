"""Read current HUD widget tree, layout and Blueprint text defaults for T17."""
import json
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools

root = Path(__file__).resolve().parent.parent
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
umg = unreal.get_default_object(unreal.UMGToolSet)
report = {}
for path in ['/Game/UI/WBP_PrototypeHUD', '/Game/UI/WBP_ScanPanel',
             '/Game/UI/WBP_RoundDecision', '/Game/UI/WBP_HealthThreat',
             '/Game/UI/WBP_BoxLocked']:
    bp = assets.load_asset(path)
    assert bp, path
    widgets = []
    for item in umg.call_method('GetWidgets', (bp,)).widgets:
        w = item.widget
        row = {'name': w.get_name(), 'class': w.get_class().get_name()}
        if isinstance(w, unreal.TextBlock):
            row['text'] = str(w.get_text())
            row['font_size'] = w.get_font_size()
        slot = w.slot
        if isinstance(slot, unreal.CanvasPanelSlot):
            layout = slot.get_layout()
            row['position'] = [layout.offsets.left, layout.offsets.top]
            row['size'] = [layout.offsets.right, layout.offsets.bottom]
            row['anchor_min'] = [layout.anchors.minimum.x, layout.anchors.minimum.y]
            row['anchor_max'] = [layout.anchors.maximum.x, layout.anchors.maximum.y]
        widgets.append(row)
    graphs = {}
    if path.endswith('WBP_PrototypeHUD'):
        for graph in BlueprintTools.list_graphs(bp):
            values = []
            for node in BlueprintTools.find_nodes(graph):
                for pin in unreal.BlueprintEditorLibrary.list_input_pins(node):
                    value = str(pin.get_pin_value())
                    if value and any(c.isalpha() for c in value):
                        values.append({'node': node.get_name(), 'value': value})
            graphs[graph.get_name()] = values
    report[path] = {'widgets': widgets, 'graphs': graphs}
out = root / 'Saved/T17/inspection.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('[T17] HUD inspection saved: ' + str(out))
