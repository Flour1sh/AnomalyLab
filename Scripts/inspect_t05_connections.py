"""Read-only inspection of the saved T05 Blueprint graph connections."""
import json
import sys
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "Scripts"))
import build_t05 as t


def node_rows(blueprint):
    rows = []
    for graph in t.B.list_graphs(blueprint):
        for node in t.B.find_nodes(graph):
            info = t.B._get_node_info(node)
            type_id = str(info.type_id)
            if any(key in type_id for key in (
                "AIMoveTo", "StartChase", "GetPlayerCharacter", "SpawnActor",
                "CallOnOutcomeResolved", "GetThreatClass", "GetCreatureSpawnPoint",
            )):
                rows.append({
                    "graph": graph.get_name(),
                    "type_id": type_id,
                    "node": str(info.node),
                    "detail": str(info),
                })
    return rows


spider = t.h.load(t.SPIDER)
box = t.h.load(t.h.BOX_PATH)
report = {
    "spider": node_rows(spider),
    "box": node_rows(box),
    "self_node_candidates": {},
}
event_graph = unreal.BlueprintEditorLibrary.find_event_graph(spider)
for query in ("Self", "自身", "reference to self", "Get Self"):
    report["self_node_candidates"][query] = list(t.B.find_node_types(event_graph, query))
out = ROOT / "Saved/T05/connections.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
unreal.log(f"[T05] CONNECTION INSPECTION PASS: {out}")
