"""Run with actual D3D12 editor RHI, compile/save authored materials before game rendering."""
import unreal, json
from pathlib import Path
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert L.load_level('/Game/Prototype/Maps/L_Prototype')
materials=[]
for folder in ['/Game/Prototype/Environment/T20','/Game/Prototype/Data/Items','/Game/Prototype/Equipment']:
    for path in A.list_assets(folder,recursive=True,include_folder=False):
        obj=A.load_asset(path)
        if isinstance(obj,unreal.Material):
            unreal.MaterialEditingLibrary.recompile_material(obj)
            materials.append(obj)
unreal.AnomalyRoundCoordinator.finish_asset_compilation()
for mat in materials:
    assert A.save_loaded_asset(mat,only_if_is_dirty=False)
Path(unreal.Paths.project_saved_dir(),'V03/material_warmup.json').write_text(json.dumps(dict(status='PASS',materials=[m.get_path_name() for m in materials]),indent=2),encoding='utf-8')
unreal.log('[V03 WARMUP] PASS')
