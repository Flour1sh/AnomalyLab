"""Import the original Blender detail kit and dress Level01. No gameplay rewrites."""
import sys, json, hashlib, shutil, math
from pathlib import Path
from datetime import datetime
import unreal
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'Scripts'))
from t20_layout import ROOMS, MAP, WALLS
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
T=unreal.AssetToolsHelpers.get_asset_tools()
ENV='/Game/Prototype/Environment/ScenePolish'
OUT=ROOT/'Saved/ScenePolish'; OUT.mkdir(exist_ok=True)
source=json.loads((ROOT/'ScenePolishAssets/mesh_manifest.json').read_text(encoding='utf-8'))
baseline=json.loads((OUT/'baseline.json').read_text(encoding='utf-8'))
assert source['status']=='PASS'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
backup=OUT/('AssetsBefore_'+datetime.now().strftime('%Y%m%dT%H%M%S%f'))
for p in [ROOT/'Content/Prototype/Maps/L_Prototype.umap',*(ROOT/'Content/Prototype/Environment/ScenePolish').glob('*.uasset')]:
    q=backup/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
assert L.load_level(MAP)
assert A.make_directory(ENV) or A.does_directory_exist(ENV)

def material(key,rgb,metal,rough,glow):
    path=ENV+'/M_SP_'+key
    m=A.load_asset(path) if A.does_asset_exist(path) else T.create_asset('M_SP_'+key,ENV,unreal.Material,unreal.MaterialFactoryNew())
    unreal.MaterialEditingLibrary.delete_all_material_expressions(m)
    c=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionConstant3Vector)
    c.set_editor_property('constant',unreal.LinearColor(*rgb,1))
    unreal.MaterialEditingLibrary.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR)
    for value,prop in [(rough,unreal.MaterialProperty.MP_ROUGHNESS),(metal,unreal.MaterialProperty.MP_METALLIC)]:
        n=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionConstant);n.set_editor_property('r',value)
        unreal.MaterialEditingLibrary.connect_material_property(n,'',prop)
    if glow:
        n=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionConstant3Vector)
        n.set_editor_property('constant',unreal.LinearColor(*(v*glow for v in rgb),1))
        unreal.MaterialEditingLibrary.connect_material_property(n,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    unreal.MaterialEditingLibrary.recompile_material(m)
    assert A.save_loaded_asset(m,only_if_is_dirty=False)
    return m

palette={key:material(key,*values) for key,values in source['palette'].items()}
palette.update({key:material(key,rgb,metal,rough,0) for key,rgb,metal,rough in [
    ('WallPaint',(.20,.265,.235),.06,.86),('Floor',(.085,.12,.12),.15,.87),('FloorSeam',(.025,.04,.04),0,.95)]})
M=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
meshes={}
for name,info in source['meshes'].items():
    path=ENV+'/'+name;fbx=ROOT/'ScenePolishAssets/fbx'/(name+'.fbx')
    obj=A.load_asset(path) if A.does_asset_exist(path) else None
    if not obj or A.get_metadata_tag(obj,'ScenePolishFBX')!=sha(fbx):
        ui=unreal.FbxImportUI()
        for key,value in [('import_mesh',True),('import_as_skeletal',False),('import_materials',False),('import_textures',False),
                          ('automated_import_should_detect_type',False),('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)]:
            ui.set_editor_property(key,value)
        data=ui.get_editor_property('static_mesh_import_data')
        for key,value in [('combine_meshes',True),('import_uniform_scale',1.),('convert_scene',True),('convert_scene_unit',True),
                          ('transform_vertex_to_absolute',True),('auto_generate_collision',False),('generate_lightmap_u_vs',False)]:
            data.set_editor_property(key,value)
        task=unreal.AssetImportTask()
        for key,value in [('filename',str(fbx)),('destination_path',ENV),('destination_name',name),('automated',True),
                          ('save',True),('replace_existing',True),('options',ui)]:task.set_editor_property(key,value)
        T.import_asset_tasks([task]);obj=A.load_asset(path)
    assert isinstance(obj,unreal.StaticMesh),name
    slots=obj.get_editor_property('static_materials')
    for index,slot in enumerate(slots):
        key=str(slot.get_editor_property('imported_material_slot_name')).replace('M_SP_','')
        if key not in palette:key=str(slot.get_editor_property('material_slot_name')).replace('M_SP_','')
        assert key in palette,(name,key)
        obj.set_material(index,palette[key])
    M.remove_collisions(obj)
    M.add_simple_collisions(obj,unreal.ScriptingCollisionShapeType.BOX)
    A.set_metadata_tag(obj,'ScenePolishFBX',sha(fbx))
    assert A.save_loaded_asset(obj,only_if_is_dirty=False)
    meshes[name]=obj

# Only replace actors owned by this generator. Retain all accepted gameplay objects.
for obj in E.get_all_level_actors():
    if obj.actor_has_tag('ScenePolishGenerated'):assert E.destroy_actor(obj)
actors=[];lights_before=[]
def actor(cls,label,xyz,yaw=0):
    o=E.spawn_actor_from_class(cls,unreal.Vector(*xyz),unreal.Rotator(pitch=0,yaw=yaw,roll=0),transient=False)
    assert o,label;o.set_actor_label('SP_'+label);o.set_editor_property('tags',['ScenePolishGenerated']);actors.append(o)
    return o
def mesh(name,label,xyz,yaw=0,scale=(1,1,1),solid=False):
    # FBX converts Blender's handedness: authored -Y fronts import as +Y.
    o=actor(unreal.StaticMeshActor,label,xyz,yaw+180);c=o.static_mesh_component
    c.set_static_mesh(meshes['SM_SP_'+name]);o.set_actor_scale3d(unreal.Vector(*scale))
    c.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
    return o
cube=A.load_asset('/Game/Prototype/Environment/T20/SM_LabModuleCube')
def bar(label,xyz,size,mat):
    o=actor(unreal.StaticMeshActor,label,xyz);o.static_mesh_component.set_static_mesh(cube)
    o.static_mesh_component.set_material(0,mat);o.static_mesh_component.set_collision_profile_name('NoCollision')
    o.set_actor_scale3d(unreal.Vector(*(v/100 for v in size)));return o
old={o.get_actor_label():o for o in E.get_all_level_actors() if o.get_actor_label().startswith('T20_')}
for key,o in old.items():
    if key.endswith('_Floor'):o.static_mesh_component.set_material(0,palette['Floor'])
    if key.startswith('T20_Wall_'):o.static_mesh_component.set_material(0,palette['WallPaint'])
    if key.endswith('_CeilingStrip'):o.static_mesh_component.set_visibility(False)
    if isinstance(o,unreal.PointLight):
        c=o.point_light_component
        lights_before.append(dict(label=key,intensity=c.get_editor_property('intensity'),units=str(c.get_editor_property('intensity_units'))))
        from t20_layout import COLOURS
        rgb=(.73,.85,.87) if key.endswith('_MainLight') else COLOURS[key.split('_')[1]]
        c.set_editor_property('light_color',unreal.Color(r=int(rgb[0]*255),g=int(rgb[1]*255),b=int(rgb[2]*255),a=255))
        if key.endswith('_MainLight'):
            c.set_editor_property('intensity',5000.)
            pos=o.get_actor_location();o.set_actor_location(unreal.Vector(pos.x,pos.y,300),False,False)
    if key.endswith('_CandidateRing') or key=='T20_EntryPad':o.static_mesh_component.set_material(0,palette['DarkMetal'])
for key,content in [('A','A / ANALYSIS'),('B','B / POWER'),('C','C / ISOLATION')]:
    o=old['T20_'+key+'_RoomTitle'];o.text_render.set_text(unreal.Text(content))
    x,y,yaw={'A':(-820,860,-90),'B':(820,860,-90),'C':(0,-1460,90)}[key]
    o.set_actor_location(unreal.Vector(x,y,310),False,False)
    o.set_actor_rotation(unreal.Rotator(pitch=0,yaw=yaw,roll=0),False)
    o.text_render.set_world_size(34.)
for key,o in old.items():
    if isinstance(o,unreal.TextRenderActor):
        area=key.split('_')[1]
        from t20_layout import COLOURS
        rgb=COLOURS.get(area,COLOURS['Entry'] if 'Return' in key or 'Entry' in key else (.8,.9,.87))
        o.text_render.set_text_render_color(unreal.Color(r=int(rgb[0]*255),g=int(rgb[1]*255),b=int(rgb[2]*255),a=255))
old['T20_EntryTitle'].set_actor_location(unreal.Vector(0,2060,310),False,False)
old['T20_EntryTitle'].text_render.set_world_size(46.)

# Recessed wall cassettes stop short of door gaps and never alter accepted collision.
wall_runs=[('EntryNorth','X',(-650,650),2080,0),('EntryWest','Y',(1080,1930),-780,90),('EntryEast','Y',(1080,1930),780,-90),
    ('AWest','Y',(-330,730),-1380,90),('BEast','Y',(-330,730),1380,-90),
    ('ANorth','X',(-1240,-400),880,0),('BNorth','X',(400,1240),880,0),
    ('ASouth','X',(-1240,-400),-480,180),('BSouth','X',(400,1240),-480,180),
    ('CWest','Y',(-1320,-680),-780,90),('CEast','Y',(-1320,-680),780,-90),('CSouth','X',(-650,650),-1480,180)]
for label,axis,(lo,hi),fixed,yaw in wall_runs:
    count=max(1,int((hi-lo)/235)+1)
    for i in range(count):
        v=lo+(hi-lo)*(i+.5)/count
        mesh('WallCassette',label+str(i),(v,fixed,65) if axis=='X' else (fixed,v,65),yaw)
for label,xyz,yaw in [('Entry',(0,900,0),180),('A',(-240,200,0),90),('B',(240,200,0),-90),('C',(0,-500,0),180)]:
    mesh('PortalFrame',label+'_Portal',xyz,yaw)

for label,x0,x1,y0,y1 in ROOMS:
    cx,cy=(x0+x1)/2,(y0+y1)/2
    for i,y in enumerate([y0+170,y1-170]):
        mesh('CeilingBeam',label+'_Beam'+str(i),(cx,y,355),scale=((x1-x0-20)/410,1,1))
        mesh('CeilingLight',label+'_Light'+str(i),(cx,y+70,373))
    mesh('ServicePipes',label+'_Pipes',(x0+150,cy,340),90,scale=(max(.7,(y1-y0-240)/300),1,1))
    # Thin seams sit below the accepted coloured navigation line/pads.
    for x in range(int(x0)+200,int(x1),200):bar(label+'_FloorX'+str(x),(x,cy,.5),(2.2,y1-y0-4,.2),palette['FloorSeam'])
    for y in range(int(y0)+200,int(y1),200):bar(label+'_FloorY'+str(y),(cx,y,.5),(x1-x0-4,2.2,.2),palette['FloorSeam'])

placements=[
 ('ReturnTerminal','Entry_ReturnTerminal',(250,2000,0),0),
 ('ResearchBench','Entry_EquipmentBench',(-620,1230,0),90),
 ('StorageCase','Entry_Storage01',(610,1880,0),0),('StorageCase','Entry_Storage02',(610,1880,74),0),
 ('ResearchBench','A_AnalysisBench',(-1260,-180,0),90),
 ('SpecimenRack','A_SpecimenRack',(-640,-360,0),180),
 ('StorageCase','A_Storage',(-650,750,0),0),
 ('PowerCabinet','B_Distribution',(1260,-210,0),-90),
 ('PowerCabinet','B_Breaker',(900,770,0),0),
 ('StorageCase','B_Storage',(550,760,0),0),
 ('ContainmentPod','C_Pod01',(580,-1400,0),180),('ContainmentPod','C_Pod02',(-580,-1400,0),180),
 ('ResearchBench','C_MonitorBench',(-670,-970,0),90),
 ('StorageCase','C_Storage',(620,-720,0),180)]
for name,label,xyz,yaw in placements:mesh(name,label,xyz,yaw,solid=True)
for label,xyz,yaw in [('Entry',(-780,1500,290),90),('A',(-1380,450,290),90),('B',(1380,400,290),-90),('C',(440,-1480,290),180)]:
    mesh('WallVent',label+'_Vent',xyz,yaw)
# Entry pad edging and candidate-pad corners, leaving the centre readable.
green=A.load_asset('/Game/Prototype/Environment/T20/M_Entry')
for x in [-320,320]:bar('EntryPadEdgeX'+str(x),(x,1700,3),(4,460,.4),green)
for y in [1470,1930]:bar('EntryPadEdgeY'+str(y),(0,y,3),(640,4,.4),green)
from t20_layout import BOX_POINTS
for label,(x,y,z) in zip(['A','B','C'],BOX_POINTS):
    colour=A.load_asset('/Game/Prototype/Environment/T20/M_'+label)
    for sx in [-1,1]:
        for sy in [-1,1]:
            bar(label+'_CornerX'+str(sx)+str(sy),(x+sx*68,y+sy*88,3),(42,4,.4),colour)
            bar(label+'_CornerY'+str(sx)+str(sy),(x+sx*88,y+sy*68,3),(4,42,.4),colour)

world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
tiles=unreal.AnomalyRoundCoordinator.build_exploration_navigation(world);assert tiles>0
unreal.AnomalyRoundCoordinator.finish_asset_compilation()
assert L.save_current_level()
for rel,digest in baseline['protected'].items():assert sha(ROOT/rel)==digest,'Protected asset changed: '+rel
report=dict(status='PASS',backup=str(backup),map=MAP,meshes=len(meshes),materials=len(palette),generated_actors=len(actors),
    solid_props=len(placements),navigation_valid_tiles=tiles,protected_assets_unchanged=len(baseline['protected']),
    lights_before=lights_before,actors=[dict(label=o.get_actor_label(),class_name=o.get_class().get_name(),
        location=[o.get_actor_location().x,o.get_actor_location().y,o.get_actor_location().z]) for o in actors])
(OUT/'build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('[SCENE POLISH] BUILD PASS')
