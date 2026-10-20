"""Repair the saved T05 chase connection and spawn/attack spacing."""
import shutil
import sys
from datetime import datetime
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "Scripts"))
import build_t05 as t


def backup_assets():
    folder = ROOT / "Saved/T05" / ("Backup_Repair_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    for asset_path in (t.SPIDER, t.h.BOX_PATH):
        relative = Path(asset_path.replace("/Game/", "") + ".uasset")
        source = ROOT / "Content" / relative
        destination = folder / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return folder


backup = backup_assets()
spider = t.h.load(t.SPIDER)
graph = unreal.BlueprintEditorLibrary.find_event_graph(spider)
move_nodes = [n for n in t.B.find_nodes(graph)
              if str(t.B._get_node_info(n).type_id).endswith("|AIMoveTo")]
assert len(move_nodes) == 1, f"Expected one AI MoveTo node, found {len(move_nodes)}"
move = move_nodes[0]
pawn_pin = t.h.find_pin(move, "in", ["Pawn"])
if not pawn_pin.list_connected_pins():
    self_node = t.h._tag(t.B.create_node(
        graph, "变量|获得一个对自身的引用", unreal.IntPoint(1100, 1760)))
    t.h.connect(self_node, ["self"], move, ["Pawn"])

sensor = next(c for c in t.components(spider) if "AttackOverlap" in c.get_name())
sensor.set_sphere_radius(80, False)
t.h.ASSETS.set_metadata_tag(spider, "T05BuildVersion", "2")
t.compile_bp(spider, True)

box = t.h.load(t.h.BOX_PATH)
point = next(c for c in t.components(box) if c.get_name().startswith("CreatureSpawnPoint"))
point.set_editor_property("relative_location", unreal.Vector(250, -300, -3))
t.h.ASSETS.set_metadata_tag(box, "T05BuildVersion", "2")
t.compile_bp(box, True)

unreal.log(f"[T05] CHASE REPAIR PASS; backup={backup}")
