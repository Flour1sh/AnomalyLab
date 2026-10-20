"""Read-only mesh dimensions and crate bounds for T11E scale review."""
import json
from pathlib import Path
import unreal
from editor_toolset.toolsets.actor import ActorTools

root = Path(__file__).resolve().parent.parent
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
result = {}
for folder, names in [('/Game/Prototype/Equipment/T11E',
                       ['SM_Scanner_Metal','SM_Scanner_Bio','SM_Scanner_Matter','SM_Gun_Placeholder']),
                      ('/Game/Prototype/Environment/BoxClues',
                       ['SM_Crate_MetalBrace','SM_Crate_WarningMarker','SM_Crate_WearPatch'])]:
    for name in names:
        mesh = assets.load_asset(folder+'/'+name)
        item = {'bound_methods':[method for method in dir(mesh) if 'bound' in method.lower()]}
        for method in ['get_bounding_box','get_bounds']:
            try:
                item[method] = str(getattr(mesh, method)())
            except Exception as exc:
                item[method+'_error'] = str(exc)
        result[name] = item
box = assets.load_asset('/Game/Anomalies/Containers/BP_AnomalyBox')
cdo = unreal.get_default_object(box.generated_class())
crate = next(c for c in ActorTools.get_components(cdo) if c.get_name().lower().startswith('cratemesh'))
crate_asset = crate.get_editor_property('skeletal_mesh_asset')
result['crate'] = {'mesh':str(crate_asset),
                   'asset_bound_methods':[method for method in dir(crate_asset) if 'bound' in method.lower()]}
for method in ['get_bounds','get_bounding_box','get_imported_bounds']:
    try: result['crate']['asset_'+method] = str(getattr(crate_asset, method)())
    except Exception as exc: result['crate']['asset_'+method+'_error'] = str(exc)
for method in ['get_local_bounds','get_bounds']:
    try: result['crate'][method] = str(getattr(crate, method)())
    except Exception as exc: result['crate'][method+'_error'] = str(exc)
output = root/'Saved/T11E/bounds_report.json'
output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[T11E] BOUNDS ' + str(output))
