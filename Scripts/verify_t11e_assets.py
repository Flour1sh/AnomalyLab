"""Independent T11E reload/reference audit; run in a fresh unattended editor."""
import json
from pathlib import Path

import unreal
from editor_toolset.toolsets.actor import ActorTools

ROOT = Path(__file__).resolve().parent.parent
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
OUTPUT = ROOT / 'Saved' / 'T11E' / 'reload_report.json'
EQUIPMENT = '/Game/Prototype/Equipment/T11E'
CLUES = '/Game/Prototype/Environment/BoxClues'
PLAYER = '/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter'
BOX = '/Game/Anomalies/Containers/BP_AnomalyBox'


def path(obj):
    return obj.get_path_name() if obj else None


def main():
    meshes = {}
    for folder, names in [(EQUIPMENT, ['SM_Scanner_Metal','SM_Scanner_Bio','SM_Scanner_Matter','SM_Gun_Placeholder']),
                          (CLUES, ['SM_Crate_MetalBrace','SM_Crate_WarningMarker','SM_Crate_WearPatch'])]:
        for name in names:
            mesh = ASSETS.load_asset(folder+'/'+name)
            assert isinstance(mesh, unreal.StaticMesh), name
            materials = [path(item.get_editor_property('material_interface'))
                         for item in mesh.get_editor_property('static_materials')]
            assert materials and all(materials), (name, materials)
            meshes[name] = {'path':path(mesh), 'materials':materials}
    palette = {}
    for folder, name, expected in [(EQUIPMENT,'M_ScreenGreen',(.06,.54,.27)),
                                   (EQUIPMENT,'M_WarningRed',(.62,.075,.045)),
                                   (EQUIPMENT,'M_ScreenBlue',(.10,.42,.58)),
                                   (CLUES,'M_WarningYellow',(.84,.57,.05))]:
        material = ASSETS.load_asset(folder+'/'+name)
        assert isinstance(material, unreal.MaterialInstanceConstant), name
        color = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(
            material, 'DiffuseColor')
        rgb = tuple(float(getattr(color, channel)) for channel in ('r','g','b'))
        assert all(abs(value-want) < .005 for value,want in zip(rgb,expected)), (name,rgb)
        palette[name] = rgb
    player = ASSETS.load_asset(PLAYER)
    box = ASSETS.load_asset(BOX)
    assert player and box
    player_cdo = unreal.get_default_object(player.generated_class())
    box_cdo = unreal.get_default_object(box.generated_class())
    components = [c for c in ActorTools.get_components(player_cdo)
                  if 'T11EEquipment' in c.get_name()]
    assert len(components) == 1, [c.get_name() for c in components]
    component = components[0]
    refs = {}
    for prop, name in [('metal_detector_mesh','SM_Scanner_Metal'),
                       ('bio_detector_mesh','SM_Scanner_Bio'),
                       ('matter_analyzer_mesh','SM_Scanner_Matter'),
                       ('gun_mesh','SM_Gun_Placeholder')]:
        refs[prop] = path(component.get_editor_property(prop))
        assert refs[prop] == meshes[name]['path'], (prop, refs[prop])
    for prop, name in [('metal_brace_mesh','SM_Crate_MetalBrace'),
                       ('warning_marker_mesh','SM_Crate_WarningMarker'),
                       ('wear_patch_mesh','SM_Crate_WearPatch')]:
        refs[prop] = path(box_cdo.get_editor_property(prop))
        assert refs[prop] == meshes[name]['path'], (prop, refs[prop])
    crate = next((c for c in ActorTools.get_components(box_cdo)
                  if c.get_name().lower().startswith('cratemesh')), None)
    assert crate, 'CrateMesh missing'
    result = {'status':'PASS','meshes':meshes,'palette':palette,'references':refs,
              'equipment_component':component.get_name(),
              'crate_component':crate.get_name(),
              'crate_scale':str(crate.get_editor_property('relative_scale3d'))}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('[T11E] RELOAD PASS ' + str(OUTPUT))


main()
