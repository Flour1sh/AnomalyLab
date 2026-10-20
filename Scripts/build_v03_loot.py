"""T21: generate four fixed item definitions and assign only Exploration map."""
from pathlib import Path
from datetime import datetime
import json
import shutil
import hashlib
import unreal

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Saved/V03'
OUT.mkdir(parents=True, exist_ok=True)
A = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
L = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
T = unreal.AssetToolsHelpers.get_asset_tools()
FOLDER = '/Game/Prototype/Data/Items'
backup = OUT / ('T21AssetsBefore_' + datetime.now().strftime('%Y%m%dT%H%M%S%f'))
for path in [ROOT/'Content/Prototype/Maps/L_Prototype.umap', *list((ROOT/'Content/Prototype/Data/Items').glob('*.uasset'))]:
    if path.exists():
        dest = backup / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
legacy = ROOT/'Content/Prototype/Maps/L_LegacyPrototype.umap'
legacy_hash = hashlib.sha256(legacy.read_bytes()).hexdigest()
definitions = []
for item_id, name, shape, scale, colour, trash in (
    ('LabChip', '实验芯片', 'Cube', (.30, .21, .07), (.05, .85, .6), False),
    ('AnomalyCore', '异常核心', 'Sphere', (.28, .28, .28), (.65, .12, .95), False),
    ('SampleCanister', '密封样本', 'Cylinder', (.19, .19, .38), (.1, .55, 1.), False),
    ('SpentBattery', '废旧电池', 'Cylinder', (.15, .15, .25), (.55, .34, .08), True)):
    mesh_path = FOLDER + '/SM_' + item_id
    mesh = A.load_asset(mesh_path) if A.does_asset_exist(mesh_path) else A.duplicate_asset('/Engine/BasicShapes/' + shape, mesh_path)
    assert mesh and A.save_loaded_asset(mesh, only_if_is_dirty=False)
    mat_path = FOLDER + '/M_' + item_id
    mat = A.load_asset(mat_path) if A.does_asset_exist(mat_path) else T.create_asset('M_' + item_id, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    unreal.MaterialEditingLibrary.delete_all_material_expressions(mat)
    rgb = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector)
    rgb.set_editor_property('constant', unreal.LinearColor(*colour, 1.))
    for prop in (unreal.MaterialProperty.MP_BASE_COLOR, unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        assert unreal.MaterialEditingLibrary.connect_material_property(rgb, '', prop)
    unreal.MaterialEditingLibrary.recompile_material(mat)
    assert A.save_loaded_asset(mat, only_if_is_dirty=False)
    path = FOLDER + '/DA_' + item_id
    factory = unreal.DataAssetFactory()
    factory.set_editor_property('data_asset_class', unreal.AnomalyItemDefinition)
    data = A.load_asset(path) if A.does_asset_exist(path) else T.create_asset('DA_' + item_id, FOLDER, unreal.AnomalyItemDefinition, factory)
    for key, value in dict(item_id=item_id, display_name=unreal.Text(name), pickable=True,
                           trash=trash, trash_value=3, mesh=mesh, material=mat,
                           mesh_scale=unreal.Vector(*scale), glow_colour=unreal.LinearColor(*colour, 1.)).items():
        data.set_editor_property(key, value)
    assert A.save_loaded_asset(data, only_if_is_dirty=False)
    definitions.append(data)
assert L.load_level('/Game/Prototype/Maps/L_Prototype')
spawners = [a for a in E.get_all_level_actors() if isinstance(a, unreal.AnomalyRoundCoordinator)]
assert len(spawners) == 1
spawners[0].set_editor_property('loot_definitions', definitions)
assert L.save_current_level()
assert hashlib.sha256(legacy.read_bytes()).hexdigest() == legacy_hash
(OUT/'T21_assets.json').write_text(json.dumps(dict(status='PASS', items=[d.get_path_name() for d in definitions],
    backup=str(backup), legacy_unchanged=True), ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('[V03 T21] PASS')

