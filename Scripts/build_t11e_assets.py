"""T11E: import Blender FBX and wire native equipment/box mesh references.

Run through cpp_migration.py editor after a successful Editor C++ build.
This script is idempotent and backs up the two existing Blueprint packages.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import unreal
from editor_toolset.toolsets.actor import ActorTools
from editor_toolset.toolsets.blueprint import BlueprintTools

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'T11EAssets' / 'fbx'
BACKUP = ROOT / 'Saved' / 'T11E' / ('BlueprintBackup_' + datetime.now().strftime('%Y%m%dT%H%M%S'))
REPORT = ROOT / 'Saved' / 'T11E' / 'build_report.json'
PLAYER = '/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter'
BOX = '/Game/Anomalies/Containers/BP_AnomalyBox'
EQUIPMENT = '/Game/Prototype/Equipment/T11E'
CLUES = '/Game/Prototype/Environment/BoxClues'
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
PALETTE = {
    'DarkMetal':(.10,.12,.13), 'Iron':(.28,.31,.30),
    'DirtyGreen':(.23,.32,.26), 'Charcoal':(.06,.075,.08),
    'WarningYellow':(.84,.57,.05), 'WarningRed':(.62,.075,.045),
    'ScreenGreen':(.06,.54,.27), 'ScreenBlue':(.10,.42,.58),
    'Copper':(.48,.30,.13),
}


def log(value):
    unreal.log('[T11E] ' + str(value))


def backup_existing_blueprints():
    BACKUP.mkdir(parents=True, exist_ok=False)
    for name, disk in [('BP_FirstPersonCharacter', ROOT/'Content/FirstPerson/Blueprints/BP_FirstPersonCharacter.uasset'),
                       ('BP_AnomalyBox', ROOT/'Content/Anomalies/Containers/BP_AnomalyBox.uasset')]:
        assert disk.is_file(), disk
        shutil.copy2(disk, BACKUP/(name+'.uasset'))
    log('Blueprint backup ' + str(BACKUP))


def import_mesh(name, destination):
    path = destination + '/' + name
    existing = ASSETS.load_asset(path) if ASSETS.does_asset_exist(path) else None
    if existing:
        assert isinstance(existing, unreal.StaticMesh), path
        return existing
    filename = SOURCE/(name+'.fbx')
    assert filename.is_file(), filename
    ui = unreal.FbxImportUI()
    ui.set_editor_property('import_mesh', True)
    ui.set_editor_property('import_as_skeletal', False)
    ui.set_editor_property('import_materials', True)
    ui.set_editor_property('import_textures', False)
    ui.set_editor_property('automated_import_should_detect_type', False)
    ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
    data = ui.get_editor_property('static_mesh_import_data')
    data.set_editor_property('combine_meshes', True)
    data.set_editor_property('import_uniform_scale', 1.0)
    data.set_editor_property('convert_scene', True)
    data.set_editor_property('convert_scene_unit', True)
    data.set_editor_property('transform_vertex_to_absolute', True)
    data.set_editor_property('auto_generate_collision', False)
    data.set_editor_property('generate_lightmap_u_vs', False)
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', str(filename))
    task.set_editor_property('destination_path', destination)
    task.set_editor_property('automated', True)
    task.set_editor_property('save', True)
    task.set_editor_property('replace_existing', False)
    task.set_editor_property('options', ui)
    TOOLS.import_asset_tasks([task])
    mesh = ASSETS.load_asset(path)
    assert isinstance(mesh, unreal.StaticMesh), f'Import failed: {path}; {task.get_editor_property("imported_object_paths")}'
    log('Imported ' + mesh.get_path_name())
    return mesh


def component(bp, needle):
    cdo = unreal.get_default_object(bp.generated_class())
    return next((c for c in ActorTools.get_components(cdo) if needle.lower() in c.get_name().lower()), None)


def wire_blueprints(meshes):
    box = ASSETS.load_asset(BOX)
    player = ASSETS.load_asset(PLAYER)
    assert box and player
    BlueprintTools.compile_blueprint(box, warnings_as_errors=True)
    box_cdo = unreal.get_default_object(box.generated_class())
    for prop, name in [('metal_brace_mesh','SM_Crate_MetalBrace'),
                       ('warning_marker_mesh','SM_Crate_WarningMarker'),
                       ('wear_patch_mesh','SM_Crate_WearPatch')]:
        box_cdo.set_editor_property(prop, meshes[name])
    assert ASSETS.save_loaded_asset(box, only_if_is_dirty=False)

    equipment = component(player, 'T11EEquipment')
    if equipment is None:
        ActorTools.add_component(player, unreal.AnomalyEquipmentComponent.static_class(), 'T11EEquipment')
        BlueprintTools.compile_blueprint(player, warnings_as_errors=True)
        equipment = component(player, 'T11EEquipment')
    assert equipment, 'Equipment component missing after compile'
    for prop, name in [('metal_detector_mesh','SM_Scanner_Metal'),
                       ('bio_detector_mesh','SM_Scanner_Bio'),
                       ('matter_analyzer_mesh','SM_Scanner_Matter'),
                       ('gun_mesh','SM_Gun_Placeholder')]:
        equipment.set_editor_property(prop, meshes[name])
    assert ASSETS.save_loaded_asset(player, only_if_is_dirty=False)
    log('Wired player equipment and box clues')


def apply_palette():
    # UE's legacy FBX importer creates material instances but defaults their
    # DiffuseColor to 0.8 grey even when Blender's node graph is coloured.
    for folder in (EQUIPMENT, CLUES):
        for name, rgb in PALETTE.items():
            material_path = folder+'/M_'+name
            material = ASSETS.load_asset(material_path) if ASSETS.does_asset_exist(material_path) else None
            if material is None:
                continue
            assert isinstance(material, unreal.MaterialInstanceConstant), material
            color = unreal.LinearColor(rgb[0],rgb[1],rgb[2],1.0)
            unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
                material, 'DiffuseColor', color)
            actual = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(
                material, 'DiffuseColor')
            assert all(abs(float(getattr(actual, channel))-value) < .005
                       for channel, value in zip(('r','g','b'), rgb)), (name, actual)
            assert ASSETS.save_loaded_asset(material, only_if_is_dirty=False)
    log('Applied FBX material palette')


def main():
    assert (SOURCE/'SM_Scanner_Metal.fbx').is_file()
    backup_existing_blueprints()
    for path in (EQUIPMENT, CLUES):
        if not ASSETS.does_directory_exist(path):
            assert ASSETS.make_directory(path)
    equipment_names = ['SM_Scanner_Metal','SM_Scanner_Bio','SM_Scanner_Matter','SM_Gun_Placeholder']
    clue_names = ['SM_Crate_MetalBrace','SM_Crate_WarningMarker','SM_Crate_WearPatch']
    meshes = {name:import_mesh(name, EQUIPMENT) for name in equipment_names}
    meshes.update({name:import_mesh(name, CLUES) for name in clue_names})
    apply_palette()
    wire_blueprints(meshes)
    result = {'status':'BUILT', 'backup':str(BACKUP),
              'meshes':{name:mesh.get_path_name() for name,mesh in meshes.items()},
              'player':PLAYER, 'box':BOX}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    log('BUILD PASS ' + str(REPORT))


main()
