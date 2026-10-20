"""Rebuild T11E low-poly equipment and crate attachments with Blender 5.1.

Run: blender --background --python generate_t11e.py
Meshes are in metres; individual FBX files use -Y Forward / Z Up.
"""
import bpy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPORT = ROOT / 'fbx'
EXPORT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1.0

PALETTE = {
    'DarkMetal': (.10, .12, .13, 1), 'Iron': (.28, .31, .30, 1),
    'DirtyGreen': (.23, .32, .26, 1), 'Charcoal': (.06, .075, .08, 1),
    'WarningYellow': (.84, .57, .05, 1), 'WarningRed': (.62, .075, .045, 1),
    'ScreenGreen': (.06, .54, .27, 1), 'ScreenBlue': (.10, .42, .58, 1),
    'Copper': (.48, .30, .13, 1),
}
MATS = {}
for name, color in PALETTE.items():
    mat = bpy.data.materials.new('M_' + name)
    mat.diffuse_color = color
    mat.use_nodes = True
    shader = next((node for node in mat.node_tree.nodes if node.type == 'BSDF_PRINCIPLED'), None)
    if shader is None:
        shader = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    output = next((node for node in mat.node_tree.nodes if node.type == 'OUTPUT_MATERIAL'), None)
    if output is None:
        output = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
    for link in list(output.inputs['Surface'].links):
        mat.node_tree.links.remove(link)
    mat.node_tree.links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Metallic'].default_value = 0.45 if name in ('Iron','DarkMetal','Copper') else 0.0
    shader.inputs['Roughness'].default_value = 0.77
    MATS[name] = mat


def box(parts, name, loc, size, material, bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(MATS[material])
    if bevel:
        mod = obj.modifiers.new('SingleBevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 1
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    parts.append(obj)
    return obj


def cylinder(parts, name, loc, radius, depth, material, vertices=8, rotation=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    obj.name = name
    if rotation: obj.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.data.materials.append(MATS[material])
    parts.append(obj)
    return obj


def finish(name, parts):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts: obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    bpy.context.scene.cursor.location = (0, 0, 0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    return obj


def scanner(name, accent, head):
    p = []
    box(p,'Housing',(.14,0,.025),(.29,.13,.10),'DirtyGreen')
    box(p,'Grip',(.02,0,-.10),(.085,.08,.20),'DarkMetal')
    box(p,'RubberGrip',(.02,0,-.13),(.09,.085,.085),'Charcoal',.002)
    box(p,'Screen',(.11,-.068,.05),(.135,.007,.055),'Charcoal',.001)
    box(p,'ScreenGlow',(.11,-.073,.05),(.10,.004,.035),accent,.001)
    for x in (.16,.20):
        cylinder(p,'Knob',(x,-.075,.008),.010,.012,'Iron',8, (math.pi/2,0,0))
    box(p,'FrontSleeve',(.295,0,.025),(.055,.145,.115),'Iron')
    if head == 'metal':
        cylinder(p,'ProbeRing',(.355,0,.025),.075,.015,'Copper',12,(0,math.pi/2,0))
        cylinder(p,'ProbeCore',(.365,0,.025),.045,.020,'Charcoal',8,(0,math.pi/2,0))
    elif head == 'bio':
        for y in (-.043,.043):
            cylinder(p,'BioAntenna',(.37,y,.055),.011,.17,'Iron',8,(0,math.pi/2,0))
            box(p,'SensorTip',(.45,y,.055),(.025,.025,.025),'WarningRed',.002)
    else:
        box(p,'MatterWedge',(.355,0,.025),(.095,.16,.065),'WarningYellow')
        for y in (-.06,.06):
            box(p,'MatterProng',(.43,y,.025),(.07,.018,.055),'Iron',.002)
    return finish(name,p)


def gun():
    p=[]
    box(p,'Receiver',(.13,0,.035),(.27,.09,.10),'DarkMetal')
    box(p,'Grip',(.02,0,-.09),(.08,.08,.19),'Charcoal')
    box(p,'Slide',(.15,0,.095),(.28,.095,.035),'Iron')
    box(p,'Front',(.32,0,.048),(.12,.07,.065),'DarkMetal')
    cylinder(p,'Muzzle',(.385,0,.05),.020,.015,'Charcoal',8,(0,math.pi/2,0))
    box(p,'Safety',(.08,-.06,.025),(.025,.025,.02),'WarningRed',.002)
    box(p,'Sight',(.25,0,.125),(.025,.025,.018),'WarningYellow',.002)
    return finish('SM_Gun_Placeholder',p)


def metal_brace():
    p=[]
    # Body-only bands sit below the opening lid; origin matches crate mesh centre.
    for y in (-.47,.47):
        box(p,'SideBand',(0,y,-.12),(.92,.035,.25),'Iron',.003)
    for x in (-.47,.47):
        box(p,'CrossBand',(x,0,-.12),(.035,.92,.25),'Iron',.003)
    for x in (-.37,.37):
        for y in (-.47,.47):
            cylinder(p,'Rivet',(x,y,-.12),.012,.008,'DarkMetal',8,(math.pi/2,0,0))
    return finish('SM_Crate_MetalBrace',p)


def warning_marker():
    p=[]
    box(p,'WarningPlate',(.475,0,-.06),(.018,.28,.18),'WarningYellow',.002)
    for y in (-.09,.09):
        box(p,'WarningStripe',(.489,y,-.06),(.007,.032,.16),'Charcoal',.001)
    cylinder(p,'MarkerBolt',(.490,0,.005),.010,.005,'DarkMetal',8,(0,math.pi/2,0))
    return finish('SM_Crate_WarningMarker',p)


def wear_patch():
    p=[]
    box(p,'ScuffedPanel',(.476,0,-.25),(.016,.48,.24),'DarkMetal',.001)
    for y,z in ((-.16,-.21),(-.05,-.27),(.1,-.20),(.17,-.31)):
        box(p,'Scratch',(.487,y,z),(.003,.08,.008),'Iron',.001)
    return finish('SM_Crate_WearPatch',p)


objects = [scanner('SM_Scanner_Metal','ScreenGreen','metal'),
           scanner('SM_Scanner_Bio','WarningRed','bio'),
           scanner('SM_Scanner_Matter','ScreenBlue','matter'),
           gun(),metal_brace(),warning_marker(),wear_patch()]

for obj in objects:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(EXPORT/(obj.name+'.fbx')),use_selection=True,
                             apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
                             axis_forward='-Y',axis_up='Z',add_leaf_bones=False)

# A gallery source .blend keeps meshes and materials editable. Export always selects one mesh.
for index, obj in enumerate(objects):
    obj.location = ((index % 4 - 1.5) * 1.35, (index // 4 - .5) * 1.5, 0)
bpy.ops.object.camera_add(location=(6.0, -7.5, 5.0))
camera = bpy.context.object
direction = -camera.location
camera.rotation_euler = direction.to_track_quat('-Z','Y').to_euler()
bpy.context.scene.camera = camera
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 8.0
bpy.ops.object.light_add(type='AREA', location=(1,-3,6))
bpy.context.object.data.energy = 350
bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.context.scene.render.resolution_x = 1400
bpy.context.scene.render.resolution_y = 850
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.context.scene.render.filepath = str(ROOT/'preview.png')
bpy.ops.render.render(write_still=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'t11e_assets.blend'))
stats = {'objects':len(objects),'materials':len(MATS),
         'meshes':{o.name:{'triangles':sum(len(poly.vertices)-2 for poly in o.data.polygons),
                             'bounds_m':[round(v,4) for v in o.dimensions]} for o in objects}}
(ROOT/'generation.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
print('T11E GENERATION PASS',stats)
