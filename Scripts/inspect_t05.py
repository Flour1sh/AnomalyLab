"""Read-only T05 preflight; commandlet Python, no MCP or PIE."""
import sys
import json
from pathlib import Path
import unreal
sys.path.insert(0, str(Path(__file__).parent))
import build_t04 as h
from editor_toolset.toolsets.blueprint import BlueprintTools as B

def main():
    box = h.load(h.BOX_PATH)
    g = unreal.BlueprintEditorLibrary.find_event_graph(box)
    out = Path(__file__).parent.parent / 'Saved/T05'
    out.mkdir(exist_ok=True)
    report = {"box_nodes": [], "candidates": [], "node_types": {}}
    for n in B.find_nodes(g):
        info = B._get_node_info(n)
        report["box_nodes"].append(str(info))
    for q in ("AIMoveTo", "AI MoveTo", "Delay", "CallOn", "GetPlayerCharacter", "EqualEqual_ObjectObject", "SetTimerByFunctionName"):
        report["node_types"][q] = list(B.find_node_types(g, q))
    import re
    doc = (Path(__file__).parent.parent / 'Docs/ASSET_MAP.md').read_text(encoding='utf-8')
    for path in re.findall(r'/Game/SciFiWorld/Meshes/SM_CreatureAlien[^\s`]+', doc):
        mesh = h.load(path)
        bounds = mesh.get_bounds()
        report['candidates'].append({'path': path, 'origin': str(bounds.origin), 'extent': str(bounds.box_extent)})
        task = unreal.AssetExportTask()
        task.object = mesh
        task.filename = str(out / (mesh.get_name() + '.obj'))
        task.automated = True
        task.prompt = False
        task.replace_identical = True
        task.exporter = unreal.StaticMeshExporterOBJ()
        unreal.Exporter.run_asset_export_task(task)
    report['box_components'] = [str(c.get_name()) + ': ' + str(c.get_editor_property('relative_location')) for c in h.ActorTools.get_components(unreal.get_default_object(box.generated_class())) if isinstance(c, unreal.SceneComponent)]
    report['mesh_api'] = [n for n in dir(unreal.StaticMeshEditorSubsystem) if any(w in n for w in ('lod','export','mesh'))]
    out = Path(__file__).parent.parent / 'Saved/T05'
    out.mkdir(exist_ok=True)
    (out/'preflight.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    unreal.log('[T05] PREFLIGHT PASS')
main()
