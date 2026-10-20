"""Rebuild only the T19 menu Widget and scenic map; never save L_Prototype."""
import hashlib
import json
import math
import random
import shutil
import struct
import wave
from datetime import datetime
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Saved/T19Menu'
MENU = '/Game/Prototype/Maps/L_MainMenu'
WIDGET = '/Game/UI/Menu/WBP_MainMenu'
LEVEL01 = '/Game/Prototype/Maps/L_Prototype'
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVEL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UMG = unreal.get_default_object(unreal.UMGToolSet)
AMBER = (.90, .42, .13, 1.)
CREAM = (.80, .82, .76, 1.)
MUTED = (.36, .43, .42, 1.)
DARK = (.018, .026, .028, .98)


def colour(rgba):
    return unreal.LinearColor(*rgba)


def backup_existing():
    destination = OUT / ('AssetsBefore_' + datetime.now().strftime('%Y%m%dT%H%M%S%f'))
    for asset, ext in ((WIDGET, '.uasset'), (MENU, '.umap')):
        source = ROOT / 'Content' / (asset.removeprefix('/Game/') + ext)
        if source.is_file():
            target = destination / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return str(destination)


def gameplay_hashes():
    paths = [ROOT / 'Content/Prototype/Maps/L_Prototype.umap']
    for folder in ('Anomalies', 'Core', 'FirstPerson', 'UI'):
        paths.extend((ROOT / 'Content' / folder).rglob('*.uasset'))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file() and '/Menu/' not in p.as_posix()}


def add(cls, name, parent=None):
    result = UMG.call_method('AddWidget', (widget, cls.static_class(), name, parent, -1))
    assert result.widget, name
    return result.widget


def variable(obj):
    UMG.call_method('ToggleWidgetAsVariable', (widget, obj, True))


def build_audio():
    """Small original PCM sounds; deterministic, local and independently rebuildable."""
    source = ROOT / 'MenuAudio'
    source.mkdir(exist_ok=True)
    sounds = {}
    for name, duration in (('S_MenuHover', .045), ('S_MenuSelect', .14), ('S_MenuRoomTone', 4.)):
        rate = 24000
        rng = random.Random(19)
        frames = bytearray()
        count = int(rate * duration)
        for i in range(count):
            t = i / rate
            if name == 'S_MenuRoomTone':
                value = .055*math.sin(2*math.pi*48*t) + .024*math.sin(2*math.pi*72*t) + .006*(rng.random()*2-1)
            else:
                envelope = min(1., t/.004) * (1-i/count)**2
                frequency = 720. if name == 'S_MenuHover' else 360. + 180.*i/count
                value = envelope*(.22*math.sin(2*math.pi*frequency*t) + .025*(rng.random()*2-1))
            frames.extend(struct.pack('<h', int(max(-1., min(1., value))*32767)))
        path = source / (name + '.wav')
        with wave.open(str(path), 'wb') as wav:
            wav.setparams((1, 2, rate, count, 'NONE', 'not compressed'))
            wav.writeframes(frames)
        task = unreal.AssetImportTask()
        task.set_editor_property('filename', str(path))
        task.set_editor_property('destination_path', '/Game/UI/Menu/Audio')
        task.set_editor_property('automated', True)
        task.set_editor_property('replace_existing', True)
        task.set_editor_property('save', True)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        sound = ASSETS.load_asset('/Game/UI/Menu/Audio/' + name)
        assert sound, name
        sound.set_editor_property('looping', name == 'S_MenuRoomTone')
        assert ASSETS.save_loaded_asset(sound, only_if_is_dirty=False)
        sounds[name] = sound
    return sounds


def position(obj, x, y, w, h, z=0):
    slot = obj.slot
    slot.set_position(unreal.Vector2D(x, y))
    slot.set_size(unreal.Vector2D(w, h))
    slot.set_z_order(z)


def image(name, parent, x, y, w, h, tint, z=0):
    obj = add(unreal.Image, name, parent)
    brush = unreal.SlateBrush()
    brush.set_editor_property('draw_as', unreal.SlateBrushDrawType.IMAGE)
    brush.set_editor_property('tint_color', unreal.SlateColor(specified_color=colour(tint)))
    obj.set_brush(brush)
    obj.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
    position(obj, x, y, w, h, z)
    return obj


def text(name, parent, content, x, y, w, h, size=20, tint=CREAM, face='Regular', spacing=0):
    obj = add(unreal.TextBlock, name, parent)
    obj.set_text(unreal.Text(content))
    font = obj.get_editor_property('font')
    font.set_editor_property('font_object', ASSETS.load_asset('/Engine/EngineFonts/Roboto'))
    font.set_editor_property('typeface_font_name', face)
    font.set_editor_property('size', size)
    font.set_editor_property('letter_spacing', spacing)
    obj.set_font(font)
    obj.set_color_and_opacity(unreal.SlateColor(specified_color=colour(tint)))
    obj.set_visibility(unreal.SlateVisibility.HIT_TEST_INVISIBLE)
    position(obj, x, y, w, h, 1)
    return obj


def button(name, parent, label, x, y, w=432, h=60, size=24):
    obj = add(unreal.Button, name, parent)
    obj.set_editor_property('is_focusable', False)
    brush = unreal.SlateBrush()
    brush.set_editor_property('draw_as', unreal.SlateBrushDrawType.IMAGE)
    brush.set_editor_property('tint_color', unreal.SlateColor(specified_color=colour((.04, .05, .05, .84))))
    hover = brush.copy()
    hover.set_editor_property('tint_color', unreal.SlateColor(specified_color=colour(AMBER)))
    pressed = brush.copy()
    pressed.set_editor_property('tint_color', unreal.SlateColor(specified_color=colour((.65, .27, .07, 1.))))
    style = unreal.ButtonStyle()
    style.set_editor_property('normal', brush)
    style.set_editor_property('hovered', hover)
    style.set_editor_property('pressed', pressed)
    style.set_editor_property('normal_padding', unreal.Margin(24., 0., 24., 0.))
    style.set_editor_property('pressed_padding', unreal.Margin(26., 1., 22., -1.))
    obj.set_style(style)
    position(obj, x, y, w, h, 2)
    label_obj = add(unreal.TextBlock, name + 'Label', obj)
    label_obj.set_text(unreal.Text(label))
    label_obj.set_font_size(size)
    label_obj.set_color_and_opacity(unreal.SlateColor(specified_color=colour(CREAM)))
    label_obj.slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_LEFT)
    label_obj.slot.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_CENTER)
    variable(obj)
    return obj


def panel(name, heading, subtitle):
    canvas = add(unreal.CanvasPanel, name, design)
    position(canvas, 0, 0, 1600, 900, 20)
    image(name + 'Scrim', canvas, 0, 0, 1600, 900, (.005, .008, .009, .86))
    image(name + 'Background', canvas, 420, 118, 760, 664, DARK)
    image(name + 'Accent', canvas, 420, 118, 760, 3, AMBER)
    text(name + 'Protocol', canvas, 'ANOMALY LAB / OPERATOR TERMINAL', 466, 152, 650, 30, 14, MUTED, spacing=120)
    text(name + 'Title', canvas, heading, 466, 202, 650, 64, 38, CREAM, 'Bold')
    text(name + 'Subtitle', canvas, subtitle, 466, 275, 650, 40, 17, MUTED)
    canvas.set_visibility(unreal.SlateVisibility.COLLAPSED)
    variable(canvas)
    return canvas


def build_widget():
    global widget, design
    widget = ASSETS.load_asset(WIDGET) if ASSETS.does_asset_exist(WIDGET) else None
    if widget is None:
        widget = UMG.call_method('CreateWidgetBlueprint', ('/Game/UI/Menu', 'WBP_MainMenu', unreal.AnomalyMainMenuWidget.static_class()))
    assert widget
    old = UMG.call_method('GetWidgets', (widget,)).widgets
    if old:
        assert UMG.call_method('RemoveWidget', (widget, old[0].widget))
    root = add(unreal.CanvasPanel, 'MenuRoot')
    # The film veil fills any aspect ratio. The authored 1600x900 UI fits inside it.
    veil = image('FilmVeil', root, 0, 0, 0, 0, (.003, .009, .011, .25))
    veil.slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(0, 0), maximum=unreal.Vector2D(1, 1)))
    veil.slot.set_offsets(unreal.Margin(0, 0, 0, 0))
    scale = add(unreal.ScaleBox, 'ResponsiveFrame', root)
    scale.set_stretch(unreal.Stretch.SCALE_TO_FIT)
    scale.slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(0, 0), maximum=unreal.Vector2D(1, 1)))
    scale.slot.set_offsets(unreal.Margin(0, 0, 0, 0))
    size = add(unreal.SizeBox, 'DesignSize', scale)
    size.set_width_override(1600.)
    size.set_height_override(900.)
    design = add(unreal.CanvasPanel, 'MenuDesign', size)
    image('LeftShade', design, 0, 0, 650, 900, (.008, .014, .016, .96))
    for i in range(96):
        image('ShadeFade%02d' % i, design, 650 + i*5.5, 0, 5.5, 900, (.008, .014, .016, .96*(1-i/96)))
    image('TopRule', design, 82, 70, 1436, 1, (.3, .4, .38, .45))
    image('StatusLED', design, 84, 40, 7, 7, AMBER)
    text('HeaderLabel', design, '异常研究设施 / 外勤终端', 104, 31, 640, 28, 15, MUTED)
    text('HeaderRight', design, 'CONTAINMENT DIVISION     /     01', 1150, 31, 400, 28, 13, MUTED, spacing=100)
    text('TitleAnomaly', design, 'ANOMALY', 80, 140, 720, 118, 86, CREAM, 'Bold', 40)
    text('TitleLab', design, 'LAB', 80, 246, 430, 120, 86, AMBER, 'Bold', 100)
    image('TitleLine', design, 86, 380, 52, 3, AMBER)
    text('Tagline', design, '未知有价。生还优先。', 156, 367, 500, 37, 21, CREAM)
    for i, (name, label, english) in enumerate((('StartButton', '开始游戏', 'DEPLOY'), ('SettingsButton', '设置', 'SETTINGS'),
                                               ('GuideButton', '操作指南', 'FIELD GUIDE'), ('QuitButton', '退出游戏', 'DISCONNECT'))):
        button(name, design, label, 84, 451+i*72, 456, 60)
        text(name+'Index', design, '0'+str(i+1), 554, 470+i*72, 40, 25, 13, MUTED)
    status = text('LaunchStatus', design, '单人行动  /  LEVEL 01 已就绪', 86, 765, 650, 35, 16, MUTED)
    variable(status)
    # Camera-feed brackets and a compact deployment label leave the scene readable.
    for index, (x, y, w, h) in enumerate(((1000, 222, 32, 2), (1000, 222, 2, 32),
                                        (1440, 222, 32, 2), (1470, 222, 2, 32),
                                        (1000, 628, 32, 2), (1000, 598, 2, 32),
                                        (1440, 628, 32, 2), (1470, 598, 2, 32))):
        image('FeedBracket'+str(index), design, x, y, w, h, (.38, .48, .44, .55))
    text('FeedLabel', design, 'FACILITY 01     /     STANDBY', 1000, 185, 500, 30, 13, MUTED, spacing=120)
    image('MissionShade', design, 980, 670, 520, 115, (.008, .014, .016, .60))
    image('MissionAccent', design, 1000, 687, 3, 82, AMBER)
    text('MissionNumber', design, '01', 1020, 674, 100, 84, 54, CREAM, 'Light')
    text('MissionName', design, '实验区', 1122, 688, 330, 40, 25, CREAM)
    text('MissionDetail', design, '观察 · 扫描 · 选择 · 生还', 1124, 733, 370, 32, 16, MUTED)
    image('FooterRule', design, 82, 827, 1436, 1, (.3, .4, .38, .45))
    text('Version', design, 'v0.3   /   ANOMALY LAB', 84, 850, 400, 30, 13, MUTED, spacing=80)
    text('NavigationHint', design, '↑ ↓ 选择     ENTER 确认     ESC 返回', 1000, 850, 520, 30, 14, MUTED)

    settings = panel('SettingsPanel', '设置', '显示与画面  /  点击选项切换')
    button('ResolutionButton', settings, '分辨率', 466, 338, 668, 58, 21)
    button('WindowModeButton', settings, '显示模式', 466, 410, 668, 58, 21)
    button('QualityButton', settings, '画面质量', 466, 482, 668, 58, 21)
    settings_status = text('SettingsStatus', settings, '', 466, 566, 680, 45, 16, MUTED)
    variable(settings_status)
    button('ApplyButton', settings, '应用设置', 466, 664, 318, 60, 22)
    button('SettingsBackButton', settings, '返回', 816, 664, 318, 60, 22)

    guide = panel('GuidePanel', '操作指南', '先观察，再决定是否承担风险。')
    guide_rows = [('W A S D  /  鼠标', '移动 / 观察'), ('SPACE', '跳跃'), ('E', '打开当前瞄准的箱子'),
                  ('按住 Q', '扫描箱子；松开或移开将取消'), ('1  /  2', '切换仪器 / 枪；决策时继续 / 撤离'), ('R', '结算后重新开始')]
    for i, (key, description) in enumerate(guide_rows):
        text('GuideKey'+str(i), guide, key, 466, 336+i*43, 230, 35, 17, AMBER)
        text('GuideAction'+str(i), guide, description, 704, 336+i*43, 440, 35, 17, CREAM)
    text('GuideRule', guide, '每轮三箱，只能打开一个。完成第二次收容后必须撤离。', 466, 616, 680, 34, 16, MUTED)
    button('GuideBackButton', guide, '返回主菜单', 466, 684, 668, 60, 22)

    quit_panel = panel('QuitPanel', '结束本次连接？', '退出游戏并返回桌面。')
    text('QuitNote', quit_panel, '实验室将在下一次启动时重新开放。', 466, 390, 680, 40, 21, CREAM)
    button('CancelQuitButton', quit_panel, '继续留在这里', 466, 592, 318, 60, 22)
    button('ConfirmQuitButton', quit_panel, '确认退出', 816, 592, 318, 60, 22)

    loading = panel('LoadingPanel', '正在进入实验区', 'LEVEL 01  /  连接已建立')
    text('LoadingNumber', loading, '01', 466, 370, 300, 170, 110, AMBER, 'Light')
    text('LoadingReminder', loading, '保持警觉。扫描结果不代表绝对安全。', 466, 602, 680, 40, 21, CREAM)
    assert UMG.call_method('CompileWidgetBlueprint', (widget,))
    BlueprintTools.compile_blueprint(widget, warnings_as_errors=True)
    defaults = unreal.get_default_object(widget.generated_class())
    defaults.set_editor_property('hover_sound', SOUNDS['S_MenuHover'])
    defaults.set_editor_property('select_sound', SOUNDS['S_MenuSelect'])
    assert ASSETS.save_loaded_asset(widget, only_if_is_dirty=False)
    return len(UMG.call_method('GetWidgets', (widget,)).widgets)


def build_map():
    # Reuse the menu-owned scenery and replace only generated MENU_ actors.
    # Never delete a loaded UWorld package or modify the gameplay package.
    if ASSETS.does_asset_exist(MENU):
        assert LEVEL.load_level(MENU)
    else:
        assert LEVEL.new_level_from_template(MENU, LEVEL01)
    removed = []
    for actor in ACTORS.get_all_level_actors():
        if actor.get_actor_label().startswith('MENU_') or isinstance(actor, (unreal.AnomalyRoundCoordinator, unreal.PlayerStart, unreal.NavMeshBoundsVolume, unreal.RecastNavMesh)):
            removed.append(actor.get_actor_label())
            assert ACTORS.destroy_actor(actor)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode', unreal.AnomalyMenuGameMode.static_class())
    camera = ACTORS.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(550, 800, 240), unreal.Rotator(), transient=False)
    camera.set_actor_label('MENU_FacilityCamera')
    camera.set_editor_property('tags', ['MenuCamera'])
    camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(camera.get_actor_location(), unreal.Vector(-250, 0, 140)), False)
    camera.camera_component.set_editor_property('field_of_view', 62.)
    camera.camera_component.set_editor_property('constrain_aspect_ratio', False)
    mesh = ASSETS.load_asset('/Game/AnimatedWoodenCrateV1/Meshes/SKM_WoodenCrate')
    assert mesh
    for i, (x, y, yaw) in enumerate(((0, 0, -10), (-40, -210, 14), (55, 220, -22))):
        crate = ACTORS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(x, y, 50), unreal.Rotator(pitch=0, yaw=yaw, roll=0), transient=False)
        crate.set_actor_label('MENU_StaticCrate_%d' % i)
        crate.skeletal_mesh_component.set_skeletal_mesh_asset(mesh)
        crate.skeletal_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        support_name = 'PROTOTYPE_CentralPedestal' if i == 0 else 'ENV_SM_Floor'
        support = next(actor for actor in ACTORS.get_all_level_actors() if actor.get_actor_label() == support_name)
        support_origin, support_extent = support.get_actor_bounds(False)
        crate_origin, crate_extent = crate.get_actor_bounds(False)
        location = crate.get_actor_location()
        location.z += support_origin.z + support_extent.z - (crate_origin.z - crate_extent.z)
        crate.set_actor_location(location, False, False)
    # Light changes affect the scenic copy only.
    for actor in ACTORS.get_all_level_actors():
        if isinstance(actor, unreal.PointLight):
            light = actor.get_component_by_class(unreal.PointLightComponent)
            light.set_intensity(1100. if 'Warning' not in actor.get_actor_label() else 1800.)
            light.set_light_color(colour((.34, .52, .54, 1.)) if 'Warning' not in actor.get_actor_label() else colour((1., .22, .035, 1.)))
    key = ACTORS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(200, 310, 230), unreal.Rotator(), transient=False)
    key.set_actor_label('MENU_AmberKey')
    key.point_light_component.set_intensity(3200.)
    key.point_light_component.set_attenuation_radius(700.)
    key.point_light_component.set_light_color(colour((1., .48, .20, 1.)))
    ambient = ACTORS.spawn_actor_from_class(unreal.AmbientSound, unreal.Vector(0, 0, 120), unreal.Rotator(), transient=False)
    ambient.set_actor_label('MENU_RoomTone')
    ambient.audio_component.set_sound(SOUNDS['S_MenuRoomTone'])
    ambient.audio_component.set_editor_property('volume_multiplier', .35)
    ambient.audio_component.set_editor_property('auto_activate', True)
    assert LEVEL.save_current_level()
    return removed


OUT.mkdir(parents=True, exist_ok=True)
before = gameplay_hashes()
baseline_path = OUT / 'gameplay_baseline_hashes.json'
if not baseline_path.exists():
    baseline_path.write_text(json.dumps(before, ensure_ascii=False, indent=2), encoding='utf-8')
backup = backup_existing()
SOUNDS = build_audio()
widget_count = build_widget()
removed = build_map()
after = gameplay_hashes()
assert before == after, 'Existing gameplay assets changed'
report = dict(status='BUILT', menu=MENU, widget=WIDGET, level01=LEVEL01,
              widget_count=widget_count, removed_from_menu_only=removed,
              gameplay_assets_unchanged=len(before), backup=backup,
              visible_validation='PENDING', physical_input='PENDING_MANUAL')
(OUT / 'build_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('[T19Menu] BUILD PASS')
