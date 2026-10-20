"""Inspect imported T11E material API before correcting palette."""
import json
from pathlib import Path
import unreal

root=Path(__file__).resolve().parent.parent
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
material=assets.load_asset('/Game/Prototype/Equipment/T11E/M_ScreenGreen')
result={'material':str(material),
        'editing_methods':[x for x in dir(unreal.MaterialEditingLibrary) if any(t in x.lower() for t in ['connect_material','create_material_expression','get_material_property','vector_parameter'])]}
for property_name in ['expressions','base_color','material_graph','parent','vector_parameter_values']:
    try:
        value=material.get_editor_property(property_name)
        result[property_name]=str(value)
        if property_name=='expressions':
            result['expression_details']=[{'type':str(v.get_class().get_name()),'name':v.get_name(),
                                           'color':str(v.get_editor_property('constant')) if 'Constant3Vector' in v.get_class().get_name() else None}
                                          for v in value]
    except Exception as exc:result[property_name+'_error']=str(exc)
output=root/'Saved/T11E/material_inspection.json'
output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[T11E] MATERIAL INSPECT '+str(output))
