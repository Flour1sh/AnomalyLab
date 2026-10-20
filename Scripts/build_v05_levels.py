"""T34 allowlisted/idempotent maps. Never save legacy maps or shared assets."""
import hashlib,json,sys
from datetime import datetime
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'Scripts'))
from t34_layout import HUB,LAB,ORIGINAL,OWN,UI,HUB_START,LAB_START,TERMINALS,VERSION
OUT=ROOT/'Saved/V05/T34';OUT.mkdir(parents=True,exist_ok=True)
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem); L=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem); U=unreal.get_default_object(unreal.UMGToolSet)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checkpoint=json.loads((ROOT/'Saved/V05/checkpoint_T33_verified.json').read_text(encoding='utf-8'))
manifest=json.loads((Path(checkpoint['snapshot'])/'manifest.json').read_text(encoding='utf-8'))
protected={r['path']:r['sha256'] for r in manifest['files'] if r['path'].startswith('Content/')}
assert all(sha(ROOT/p)==h for p,h in protected.items()),'Legacy Content drifted before T34 build'
def world(): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
def actor(cls,name,xyz=(0,0,0),yaw=0):
    obj=E.spawn_actor_from_class(cls,unreal.Vector(*xyz),unreal.Rotator(pitch=0,yaw=yaw,roll=0),transient=False)
    assert obj,name
    obj.set_actor_label('T34_'+name);obj.set_editor_property('tags',['T34Owned']);return obj
def block(name,xyz,size,mat,collision=True):
    obj=actor(unreal.StaticMeshActor,name,xyz); c=obj.static_mesh_component;c.set_static_mesh(CUBE);c.set_material(0,mat);c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    obj.set_actor_scale3d(unreal.Vector(*(v/100 for v in size)));return obj
def sign(name,text,xyz,yaw=90,size=32):
    obj=actor(unreal.TextRenderActor,name,xyz,yaw);t=obj.text_render;t.set_text(unreal.Text(text));t.set_world_size(size);t.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER);t.set_text_render_color(unreal.Color(205,238,216,255));t.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION);return obj
def mesh(name,path,xyz,yaw=0):
    obj=actor(unreal.StaticMeshActor,name,xyz,yaw);m=A.load_asset(path);assert m,path;obj.static_mesh_component.set_static_mesh(m);obj.static_mesh_component.set_collision_profile_name('NoCollision');return obj
def light(name,xyz,intensity,radius,colour):
    obj=actor(unreal.PointLight,name,xyz);c=obj.point_light_component;c.set_mobility(unreal.ComponentMobility.MOVABLE);c.set_editor_property('intensity',intensity);c.set_editor_property('attenuation_radius',radius);c.set_editor_property('light_color',unreal.Color(*colour,255))
def material(name,rgb,glow=0):
    path=OWN+'/Environment/'+name;m=A.load_asset(path) if A.does_asset_exist(path) else None
    if m and A.get_metadata_tag(m,'T34MaterialVersion')=='1':return m
    m=m or unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,OWN+'/Environment',unreal.Material,unreal.MaterialFactoryNew())
    assert m
    unreal.MaterialEditingLibrary.delete_all_material_expressions(m)
    c=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);c.set_editor_property('constant',unreal.LinearColor(*rgb,1));unreal.MaterialEditingLibrary.connect_material_property(c,'',unreal.MaterialProperty.MP_BASE_COLOR)
    if glow:
        g=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionConstant3Vector);g.set_editor_property('constant',unreal.LinearColor(*(v*glow for v in rgb),1));unreal.MaterialEditingLibrary.connect_material_property(g,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    rough=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionConstant);rough.set_editor_property('r',.8);unreal.MaterialEditingLibrary.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    A.set_metadata_tag(m,'T34MaterialVersion','1');unreal.MaterialEditingLibrary.recompile_material(m);assert A.save_loaded_asset(m,only_if_is_dirty=False);return m
def widget():
    bp=A.load_asset(UI) if A.does_asset_exist(UI) else U.call_method('CreateWidgetBlueprint',(OWN+'/UI','WBP_Hub',unreal.AnomalyHubWidget.static_class()))
    assert bp
    if A.get_metadata_tag(bp,'T34WidgetVersion')=='1':return bp
    old=U.call_method('GetWidgets',(bp,)).widgets
    if old:U.call_method('RemoveWidget',(bp,old[0].widget))
    root=U.call_method('AddWidget',(bp,unreal.CanvasPanel.static_class(),'HubCanvas',None,-1)).widget
    specs=[('HubTitle',unreal.TextBlock,(0,0),(28,24),(850,85),(0,0),26,10),('HubGuide',unreal.TextBlock,(.5,1),(0,-100),(850,80),(.5,0),20,10),('HubFocus',unreal.TextBlock,(.5,.5),(0,40),(800,45),(.5,.5),22,10),('PanelBacking',unreal.Image,(.5,.5),(0,0),(1050,610),(.5,.5),0,30),('HubPanel',unreal.TextBlock,(.5,.5),(0,0),(980,560),(.5,.5),24,31)]
    for name,cls,anchor,pos,size,align,font,z in specs:
        item=U.call_method('AddWidget',(bp,cls.static_class(),name,root,-1)).widget;s=item.slot;s.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(*anchor),maximum=unreal.Vector2D(*anchor)));s.set_position(unreal.Vector2D(*pos));s.set_size(unreal.Vector2D(*size));s.set_alignment(unreal.Vector2D(*align));s.set_z_order(z)
        if font:
            item.set_text(unreal.Text(''));item.set_font_size(font);item.set_auto_wrap_text(True);item.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(.87,.96,.88,1)));item.set_shadow_offset(unreal.Vector2D(1,1));item.set_shadow_color_and_opacity(unreal.LinearColor(0,0,0,1));item.set_editor_property('justification',unreal.TextJustify.CENTER if name in ['HubGuide','HubFocus'] else unreal.TextJustify.LEFT)
        else:item.set_color_and_opacity(unreal.LinearColor(.012,.024,.018,.97))
        U.call_method('ToggleWidgetAsVariable',(bp,item,True))
    BlueprintTools.compile_blueprint(bp,warnings_as_errors=True);A.set_metadata_tag(bp,'T34WidgetVersion','1');assert A.save_loaded_asset(bp,only_if_is_dirty=False);return bp
def menu_widget():
    path=OWN+'/UI/WBP_MainMenu_V05'
    bp=A.load_asset(path) if A.does_asset_exist(path) else A.duplicate_asset('/Game/UI/Menu/WBP_MainMenu',path)
    assert bp
    if A.get_metadata_tag(bp,'T34MenuVersion')=='1':return
    widgets={str(x.widget.get_name()):x.widget for x in U.call_method('GetWidgets',(bp,)).widgets if x.widget}
    widgets['Version'].set_text(unreal.Text('v0.5 DEVELOPMENT   /   ANOMALY LAB'))
    BlueprintTools.compile_blueprint(bp,warnings_as_errors=True);A.set_metadata_tag(bp,'T34MenuVersion','1');assert A.save_loaded_asset(bp,only_if_is_dirty=False)
def nav():
    w=world();bounds=[x for x in E.get_all_level_actors() if isinstance(x,unreal.NavMeshBoundsVolume)];assert len(bounds)==1
    unreal.NavigationSystemV1.get_navigation_system(w).on_navigation_bounds_updated(bounds[0])
    for x in E.get_all_level_actors():
        if isinstance(x,unreal.RecastNavMesh):x.set_editor_property('runtime_generation',unreal.RuntimeGenerationType.DYNAMIC)
    tiles=unreal.AnomalyRoundCoordinator.build_exploration_navigation(w);assert tiles>0,'No valid navigation tiles';assert L.save_current_level();return tiles
def fingerprint():
    result=[]
    for x in E.get_all_level_actors():
        if x.get_actor_label().startswith('T34_') or isinstance(x,(unreal.PlayerStart,unreal.AnomalyRoundCoordinator)):
            result.append(dict(label=x.get_actor_label(),cls=x.get_class().get_path_name(),xyz=[round(v,3) for v in x.get_actor_location().to_tuple()]))
    return sorted(result,key=lambda x:x['label'])
assert (HUB,LAB)==('/Game/Maps/L_Hub','/Game/Maps/L_Lab')
widget();menu_widget();CUBE=A.load_asset('/Engine/BasicShapes/Cube');assert CUBE
warm=material('M_HubWarm',(.8,.55,.26),3);mint=material('M_HubMint',(.14,.5,.32),1)
hub_wall=material('M_HubWall',(.38,.27,.12));hub_floor=material('M_HubFloor',(.20,.17,.12))
palette={n:A.load_asset('/Game/Prototype/Environment/ScenePolish/M_SP_'+n) for n in ['WallPaint','Floor','DarkMetal','OffWhite','DirtyGreen','WarningYellow']};assert all(palette.values())
SP='/Game/Prototype/Environment/ScenePolish/'
created_hub=not A.does_asset_exist(HUB)
if created_hub:assert L.new_level_from_template(HUB,ORIGINAL)
else:assert L.load_level(HUB)
for x in list(E.get_all_level_actors()):
    keep=isinstance(x,(unreal.NavMeshBoundsVolume,unreal.RecastNavMesh,unreal.WorldSettings,unreal.PostProcessVolume)) or x.get_class().get_name() in ['DefaultPhysicsVolume','Brush']
    if not keep:assert E.destroy_actor(x),x.get_actor_label()
world().get_world_settings().set_editor_property('default_game_mode',unreal.AnomalyHubGameMode.static_class())
block('Hub_Floor',(0,0,-10),(1600,2000,20),hub_floor);block('Hub_Ceiling',(0,0,410),(1620,2020,20),palette['DarkMetal'])
for i,(xyz,size) in enumerate([((-810,0,200),(20,2040,400)),((810,0,200),(20,2040,400)),((0,1010,200),(1600,20,400)),((0,-1010,200),(1600,20,400))]):
    block('Hub_Wall_'+str(i),xyz,size,hub_wall);block('Hub_Skirt_'+str(i),(xyz[0],xyz[1],35),(size[0]+2,size[1]+2,70),palette['DirtyGreen'])
for x in [-400,0,400]:
    for y in [-600,0,600]:
        block('Hub_FloorSeam_%s_%s'%(x,y),(x,y,.4),(3,350,1),palette['DarkMetal'],False)
for y in [-700,0,700]:
    light('Hub_MainLight_'+str(y),(0,y,345),6500,1050,(255,211,160));block('Hub_LightStrip_'+str(y),(0,y,398),(300,18,3),warm,False)
light('Hub_ShopLight',(-550,100,300),1800,550,(255,225,174));light('Hub_ReportLight',(550,550,300),1400,500,(181,240,209))
block('Hub_DepartureLine',(0,-100,.7),(8,1350,1),mint,False);block('Hub_StartPad',(0,500,.6),(350,240,1),palette['DirtyGreen'],False)
for name,xyz,yaw in TERMINALS:
    terminal=actor(unreal.AnomalyHubTerminal,'Hub_'+name,xyz,yaw)
    terminal.set_editor_property('kind',getattr(unreal.AnomalyHubTerminalKind,name.upper()))
    visual=terminal.get_editor_property('visual');visual.set_static_mesh(A.load_asset(SP+'SM_SP_ReturnTerminal'));visual.set_relative_location(unreal.Vector(0,0,-95),False,False)
    if name!='Departure':
        sign('Hub_'+name+'_Sign',name.upper(),(xyz[0]+(-220 if xyz[0]<0 else 220),xyz[1],260),yaw=0 if xyz[0]<0 else 180,size=32)
mesh('Hub_DepartureFrame',SP+'SM_SP_PortalFrame',(0,-920,0));block('Hub_DepartureDoors',(0,-950,145),(310,20,290),palette['DarkMetal']);sign('Hub_DepartureLabel','LAB / DEPARTURE',(0,-925,280),90,38)
sign('Hub_Title','SAFE BASE  /  HUB',(0,985,280),-90,42);sign('Hub_ExitGuide','PREPARE  >  EXPLORE  >  RETURN',(0,-990,340),90,26)
for i,x in enumerate([-650,650]):
    mesh('Hub_Storage_'+str(i),SP+'SM_SP_StorageCase',(x,820,0));block('Hub_StorageBlock_'+str(i),(x,820,45),(150,90,90),palette['DarkMetal']).set_actor_hidden_in_game(True)
mesh('Hub_Bench',SP+'SM_SP_ResearchBench',(-650,-450,0),90);block('Hub_BenchBlock',(-650,-450,70),(100,225,140),palette['DarkMetal']).set_actor_hidden_in_game(True)
start=actor(unreal.PlayerStart,'PlayerStart_Hub',HUB_START,-90)
for x in E.get_all_level_actors():
    if isinstance(x,unreal.NavMeshBoundsVolume):x.set_actor_location(unreal.Vector(0,0,150),False,False);x.set_actor_scale3d(unreal.Vector(9,11,4))
hub_tiles=nav();hub_signature=fingerprint();hub_actor_count=len(E.get_all_level_actors())
created_lab=not A.does_asset_exist(LAB)
if created_lab:assert L.new_level_from_template(LAB,ORIGINAL)
else:assert L.load_level(LAB)
for x in list(E.get_all_level_actors()):
    if x.get_actor_label().startswith('T34_') and not isinstance(x,unreal.PlayerStart):assert E.destroy_actor(x)
coordinators=[x for x in E.get_all_level_actors() if isinstance(x,unreal.AnomalyRoundCoordinator)];assert len(coordinators)==1
c=coordinators[0];c.set_editor_property('use_preparation',False);c.set_editor_property('await_level_launch',True)
starts=[x for x in E.get_all_level_actors() if isinstance(x,unreal.PlayerStart)];assert len(starts)==1
starts[0].set_actor_label('T34_PlayerStart_Lab');starts[0].set_actor_location(unreal.Vector(*LAB_START),False,False);starts[0].set_actor_rotation(unreal.Rotator(pitch=0,yaw=-90,roll=0),False)
for x in E.get_all_level_actors():
    if isinstance(x,unreal.TextRenderActor) and x.get_actor_label()=='T20_EntryTitle':x.text_render.set_text(unreal.Text('EXTRACTION AIRLOCK'))
sign('Lab_AirlockGuide','RETURN  /  E TO EXTRACT',(0,2059,235),-90,24)
lab_tiles=nav();lab_signature=fingerprint();lab_actor_count=len(E.get_all_level_actors())
assert all(sha(ROOT/p)==h for p,h in protected.items()),'Protected legacy Content changed'
signature=dict(hub=hub_signature,lab=lab_signature,hub_actor_count=hub_actor_count,lab_actor_count=lab_actor_count)
previous=OUT/'latest_build.json';idempotent=None
if previous.exists():
    old=json.loads(Path(json.loads(previous.read_text(encoding='utf-8'))['report']).read_text(encoding='utf-8'))
    if old.get('layout_version',1)==VERSION:
        idempotent=old['signature']==signature;assert idempotent,'Actor count/layout drift on regeneration'
stamp=datetime.now().strftime('%Y%m%dT%H%M%S');report=OUT/('build_'+stamp+'.json')
data=dict(status='PASS',layout_version=VERSION,maps=[HUB,LAB],created=dict(hub=created_hub,lab=created_lab),signature=signature,navigation_tiles=dict(hub=hub_tiles,lab=lab_tiles),protected_legacy_content=len(protected),idempotence_verified=idempotent,visual='PENDING_RUNTIME',gameplay_transactions='T35/T36 pending; no false success')
report.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');previous.write_text(json.dumps(dict(status='PASS',report=str(report)),indent=2),encoding='utf-8')
unreal.log('[T34 BUILD] PASS')
