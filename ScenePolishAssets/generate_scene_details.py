"""Authored low-poly laboratory kit. Background Blender only; no live scene changed."""
from pathlib import Path
import math, json
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
FBX = ROOT / 'fbx'
FBX.mkdir(parents=True, exist_ok=True)
PALETTE = {
    'DarkMetal': ((.10,.12,.13), .5, .82, 0),
    'Iron': ((.28,.31,.30), .4, .76, 0),
    'DirtyGreen': ((.23,.32,.26), .2, .86, 0),
    'Charcoal': ((.035,.045,.05), .1, .9, 0),
    'WarningYellow': ((.84,.57,.05), .05, .75, 0),
    'Copper': ((.48,.30,.13), .45, .78, 0),
    'ScreenGreen': ((.06,.54,.27), 0, .5, 1.4),
    'ScreenBlue': ((.10,.42,.58), 0, .5, 1.4),
    'ColdLight': ((.55,.75,.90), 0, .4, 2),
    'OffWhite': ((.54,.58,.53), .1, .85, 0),
}
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for m in list(bpy.data.materials): bpy.data.materials.remove(m)
MATS={}
for key,(rgb,metal,rough,emission) in PALETTE.items():
    m=bpy.data.materials.new('M_SP_'+key);m.diffuse_color=(*rgb,1);m.use_nodes=True
    s=m.node_tree.nodes.get('Principled BSDF')
    for field,value in [('Base Color',(*rgb,1)),('Metallic',metal),('Roughness',rough),('Emission Color',(*rgb,1)),('Emission Strength',emission)]:
        s.inputs[field].default_value=value
    MATS[key]=m

parts=[]; meshes={}; report={}
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def finish(o,key,bevel):
    active(o);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    o.data.materials.append(MATS[key])
    if bevel:
        mod=o.modifiers.new('Single_edge_bevel','BEVEL');mod.width=bevel;mod.segments=1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in o.data.polygons:p.use_smooth=False
    parts.append(o);return o
def box(xyz, size, key='DarkMetal', bevel=.015, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1,location=xyz,rotation=rot)
    o=bpy.context.object;o.dimensions=size;return finish(o,key,bevel)
def cyl(xyz, radius, depth, key='Iron', axis='Z', vertices=8):
    rotation={'Z':(0,0,0),'X':(0,math.pi/2,0),'Y':(math.pi/2,0,0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=xyz,rotation=rotation)
    return finish(bpy.context.object,key,.008)
def face_screen(x,y,z,w,h,key='ScreenGreen'):
    box((x,y,z),(w+.08,.055,h+.08),'Charcoal',.015)
    box((x,y-.033,z),(w,.012,h),key,.003)
def indicators(x,y,z,count=3):
    for i in range(count):box((x+i*.09,y,z),(.045,.02,.035),'ScreenGreen',.003)
def vents(x,y,z,width=.65,count=5):
    for i in range(count):box((x,y,z+i*.085),(width,.03,.035),'Charcoal',.003)
def join(name):
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:p.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object
    o.name=name;o.data.name=name;bpy.context.scene.cursor.location=(0,0,0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    # Export local floor-centred coordinates, never a baked asset-gallery offset.
    bpy.ops.export_scene.fbx(filepath=str(FBX/(name+'.fbx')),use_selection=True,object_types={'MESH'},
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',use_mesh_modifiers=True,
        axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE')
    lo=[min(v.co[a] for v in o.data.vertices) for a in range(3)]
    hi=[max(v.co[a] for v in o.data.vertices) for a in range(3)]
    tris=sum(len(p.vertices)-2 for p in o.data.polygons)
    assert all(math.isfinite(v) for v in (*lo,*hi)) and tris<6500
    assert abs(lo[2])<.03,(name,lo)
    report[name]=dict(triangles=tris,dimensions_m=[hi[a]-lo[a] for a in range(3)],
        bounds_min_m=lo,bounds_max_m=hi,materials=[m.name for m in o.data.materials],fbx=str(FBX/(name+'.fbx')))
    meshes[name]=o;parts.clear()

# 1: repeated wall cassette with a recessed centre and broad, clean silhouette.
box((0,0,1.1),(2,.12,2.2),'DarkMetal')
box((0,-.075,1.18),(1.82,.065,1.87),'DirtyGreen')
for x in [-.87,.87]:box((x,-.13,1.18),(.035,.035,1.82),'Iron',.005)
box((0,-.14,.32),(1.7,.025,.035),'Iron',.003)
for x in [-.82,.82]:
    for z in [.42,1.95]:cyl((x,-.14,z),.025,.015,'Iron','Y')
join('SM_SP_WallCassette')
# 2: a 3.6m clear portal; trim sits on the wall ends, not in the walking opening.
for x in [-1.94,1.94]:
    box((x,0,1.7),(.28,.3,3.4),'DarkMetal')
    box((x,-.17,1.7),(.07,.035,2.6),'OffWhite',.005)
    box((x,-.19,.44),(.16,.03,.26),'WarningYellow',.004)
box((0,0,3.58),(4.16,.32,.36),'DarkMetal')
box((0,-.18,3.57),(2.4,.02,.065),'ColdLight',.003)
join('SM_SP_PortalFrame')
# 3: paired overhead 8-sided pipes, ribs and clamps.
for y,key in [(-.14,'Iron'),(.14,'Copper')]:
    cyl((0,y,.12),.085,3,key,'X')
    for x in [-1.2,0,1.2]:cyl((x,y,.12),.105,.07,'DarkMetal','X')
for x in [-1.15,1.15]:box((x,0,.25),(.09,.5,.09),'DarkMetal')
join('SM_SP_ServicePipes')
# 4: utilitarian twin-tube luminaire; guards create visible depth at the ceiling.
box((0,0,.12),(1.65,.42,.24),'DarkMetal')
for y in [-.11,.11]:box((0,y,.018),(1.43,.075,.03),'ColdLight',.008)
for x in [-.65,0,.65]:box((x,0,-.005),(.035,.41,.04),'Iron',.005)
# fixtures are ceiling anchored, allow a 2cm below-origin guard.
join('SM_SP_CeilingLight')
# 5: work bench with drawers, instrument panel and specimen tray.
for x in [-.91,.91]:
    box((x,0,.49),(.18,.64,.98),'DarkMetal')
box((0,0,1.02),(2.2,.82,.12),'OffWhite')
box((-.58,-.01,.61),(.67,.67,.72),'DirtyGreen')
for z in [.39,.67,.91]:
    box((-.58,-.36,z),(.59,.045,.18),'Iron',.008)
    box((-.58,-.4,z),(.2,.045,.025),'Charcoal',.003)
box((.44,.14,1.15),(.67,.46,.16),'DarkMetal')
face_screen(.44,-.102,1.19,.46,.09,'ScreenBlue')
box((-.43,.10,1.15),(.43,.4,.13),'Iron')
for x in [-.53,-.36]:cyl((x,.1,1.36),.055,.32,'OffWhite')
join('SM_SP_ResearchBench')
# 6: specimen rack with sealed 8-sided canisters, fixed rather than pickup-like.
for x in [-.67,.67]:box((x,.08,1.12),(.1,.65,2.24),'DarkMetal')
box((0,.34,1.12),(1.38,.08,2.24),'DirtyGreen')
for z in [.08,.73,1.38,2.17]:box((0,0,z),(1.4,.65,.09),'Iron')
for z in [.38,1.04,1.70]:
    for x in [-.4,0,.4]:
        cyl((x,0,z),.105,.40,'OffWhite');cyl((x,0,z+.21),.115,.055,'DarkMetal')
        box((x,-.105,z),(.14,.025,.13),'DirtyGreen',.004)
join('SM_SP_SpecimenRack')
# 7: power distribution cabinet, rotary breaker, louvers, warning stripe.
box((0,0,1.20),(1.6,.75,2.4),'DarkMetal')
box((0,-.40,1.35),(1.43,.06,1.87),'DirtyGreen')
for x in [-.73,.73]:box((x,-.44,1.35),(.035,.025,1.8),'Iron',.004)
face_screen(-.34,-.45,1.91,.39,.24)
cyl((.4,-.48,1.93),.13,.10,'WarningYellow','Y')
box((.4,-.55,1.93),(.035,.045,.21),'Charcoal',.003)
vents(0,-.46,.65,1.04,6);indicators(-.43,-.48,1.56,4)
box((0,-.46,.21),(1.47,.025,.13),'WarningYellow',.004)
join('SM_SP_PowerCabinet')
# 8: containment pod, recessed opaque window and mechanical lock.
box((0,0,1.15),(1.4,.8,2.3),'DarkMetal')
for x in [-.62,.62]:box((x,-.43,1.23),(.13,.14,1.98),'OffWhite')
face_screen(0,-.44,1.40,.95,1.15,'Charcoal')
for x in [-.4,.4]:box((x,-.50,1.4),(.035,.025,1.03),'ScreenBlue',.003)
box((0,-.52,1.88),(.72,.025,.05),'ScreenBlue',.003)
cyl((.35,-.55,.51),.14,.1,'Iron','Y')
box((.35,-.62,.51),(.22,.035,.035),'WarningYellow',.004)
indicators(-.43,-.53,.52,3)
join('SM_SP_ContainmentPod')
# 9: closed storage, differentiated from the interactive wooden anomaly crates.
box((0,0,.35),(.8,.65,.7),'DirtyGreen')
box((0,0,.7),(.84,.69,.08),'DarkMetal')
for x in [-.3,.3]:box((x,-.34,.37),(.045,.035,.58),'Iron',.005)
box((0,-.35,.42),(.22,.025,.13),'OffWhite',.004)
box((0,-.38,.22),(.18,.055,.055),'Charcoal',.005)
join('SM_SP_StorageCase')
# 10: wall ventilation with deep louvers.
box((0,0,.4),(1.2,.13,.8),'DarkMetal')
for z in [.16,.29,.42,.55,.68]:box((0,-.10,z),(1.04,.12,.065),'Iron',.004,rot=(math.radians(20),0,0))
join('SM_SP_WallVent')
# 11: return terminal. Decorative screen only, extraction still uses existing E.
box((0,0,.10),(.8,.6,.2),'DarkMetal')
box((0,.08,.63),(.46,.4,1.08),'DirtyGreen')
box((0,.0,1.35),(.8,.55,.5),'DarkMetal')
face_screen(0,-.29,1.38,.60,.28)
indicators(-.27,-.32,1.12,3)
box((0,-.33,1.02),(.42,.2,.06),'Iron')
join('SM_SP_ReturnTerminal')
# 12: overhead beam with triangular-looking bevels and paired wall brackets.
box((0,0,.15),(4.1,.26,.30),'DarkMetal',.04)
for x in [-1.9,1.9]:box((x,0,.17),(.27,.42,.34),'Iron',.03)
join('SM_SP_CeilingBeam')

assert len(meshes)==12
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
(ROOT/'mesh_manifest.json').write_text(json.dumps(dict(status='PASS',style='Flat shading; single-segment bevel; 8-sided cylinders; existing T11E palette; metres; local floor-centred origin',palette=PALETTE,meshes=report),indent=2),encoding='utf-8')
# Editable catalogue: export already happened at the origin.
for i,(name,o) in enumerate(meshes.items()):
    o.location=((i%3-1)*5.2,(i//3-1.5)*4.4,.05)
    o['asset_name']=name;o['export_origin']='local bottom centre'
box((0,0,-.12),(18,20,.24),'Charcoal',.02)
parts.clear()
world=scene.world or bpy.data.worlds.new('Studio');scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.16,.18,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.5
def light(name,xyz,energy,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=xyz
    o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
light('Key',(2,-7,15),4000,10);light('Fill',(-9,-2,10),2200,8);light('Rim',(5,9,13),3300,7)
d=bpy.data.cameras.new('Catalogue');c=bpy.data.objects.new('Catalogue',d);scene.collection.objects.link(c)
c.location=(16,-23,20);c.rotation_euler=(Vector((0,0,.7))-c.location).to_track_quat('-Z','Y').to_euler()
d.type='ORTHO';d.ortho_scale=25;scene.camera=c
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1500;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'lab_details.blend'))
scene.render.filepath=str(ROOT/'asset_catalogue.png');bpy.ops.render.render(write_still=True)
print('SCENE POLISH BLENDER PASS',len(meshes),sum(r['triangles'] for r in report.values()))
