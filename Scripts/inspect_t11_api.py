"""Read local Unreal Python API and box graph; no saves or gameplay."""
import json
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as B
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Saved/T11'
OUT.mkdir(parents=True, exist_ok=True)
report = {}
for name in dir(unreal):
    if ('Struct' in name and ('Editor' in name or 'Library' in name or 'Factory' in name)) or name in ('BlueprintGraphEditor','BlueprintGraphPinLibrary','UserDefinedStruct'):
        cls = getattr(unreal, name)
        report[name] = {m: str(getattr(cls,m).__doc__) for m in dir(cls) if not m.startswith('_') and any(s in m for s in ('variable','struct','member','pin','field','default'))}
bp = unreal.load_asset('/Game/Anomalies/Containers/BP_AnomalyBox')
graphs = {}
for g in B.list_graphs(bp):
    graphs[g.get_name()] = [dict(name=n.get_name(),type=str(B._get_node_info(n).type_id),pins=[dict(name=str(p.get_pin_name()), value=str(p.get_pin_value()), links=[p2.get_owning_node().get_name()+'.'+str(p2.get_pin_name()) for p2 in p.list_connected_pins()]) for p in list(unreal.BlueprintEditorLibrary.list_input_pins(n))+list(unreal.BlueprintEditorLibrary.list_output_pins(n))]) for n in B.find_nodes(g)]
report['graphs'] = graphs
(OUT/'api.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[T11] API INSPECTION PASS')
