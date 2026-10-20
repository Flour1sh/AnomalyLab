"""Procedurally build a low-poly industrial laboratory room in Blender.

Run with:
    blender --background --factory-startup --python generate_lab_room.py

The script has no external dependencies.  It creates the scene, validates the
important prototype constraints, renders a preview, saves the .blend file, and
exports a UE5-oriented FBX beside this script.
"""

from pathlib import Path
import math

import bpy
from mathutils import Vector


# -----------------------------------------------------------------------------
# Main parameters

BASE_ROOM_WIDTH = 8.0
BASE_ROOM_LENGTH = 10.0

# Expanded footprint. Props retain their original dimensions and are moved as
# logical groups so a monitor remains on its desk and crates remain on shelves.
ROOM_WIDTH = 16.0
ROOM_LENGTH = 20.0
ROOM_HEIGHT = 4.0

LAYOUT_SCALE_X = ROOM_WIDTH / BASE_ROOM_WIDTH
LAYOUT_SCALE_Y = ROOM_LENGTH / BASE_ROOM_LENGTH
DOOR_CENTER_X = 2.15 * LAYOUT_SCALE_X
DOOR_Y = -ROOM_LENGTH * 0.5 + 0.12

BEVEL_WIDTH = 0.02
PIPE_RADIUS = 0.12
PIPE_SEGMENTS = 8

OUTPUT_DIR = Path(__file__).resolve().parent
BLEND_PATH = OUTPUT_DIR / "low_poly_lab_room.blend"
FBX_PATH = OUTPUT_DIR / "low_poly_lab_room.fbx"
PREVIEW_PATH = OUTPUT_DIR / "low_poly_lab_preview.png"

COLORS = {
    "dark_metal": (0.10, 0.12, 0.13),
    "gray_metal": (0.25, 0.27, 0.27),
    "dirty_green": (0.22, 0.30, 0.25),
    "warning_yellow": (0.85, 0.60, 0.05),
    "warning_red": (0.65, 0.05, 0.04),
    "black": (0.018, 0.022, 0.024),
    "screen_green": (0.05, 0.70, 0.35),
    "cold_light": (0.55, 0.75, 0.90),
    "wood": (0.28, 0.16, 0.08),
}

COLLECTIONS = {}
MATERIALS = {}


# -----------------------------------------------------------------------------
# General helpers

def clear_scene():
    """Remove all objects, child collections, materials, meshes and lights."""
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            datablocks.remove(datablock)


def create_collections():
    root = bpy.data.collections.new("LowPolyLab")
    bpy.context.scene.collection.children.link(root)
    COLLECTIONS["root"] = root
    for name in ("Architecture", "Props", "Pipes", "Lights", "Gameplay"):
        collection = bpy.data.collections.new(name)
        root.children.link(collection)
        COLLECTIONS[name] = collection


def move_to_collection(obj, collection_name):
    target = COLLECTIONS[collection_name]
    for old_collection in list(obj.users_collection):
        old_collection.objects.unlink(obj)
    target.objects.link(obj)


def activate_only(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_transforms(obj):
    activate_only(obj)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def set_origin_world(obj, point):
    previous_cursor = bpy.context.scene.cursor.location.copy()
    bpy.context.scene.cursor.location = point
    activate_only(obj)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
    bpy.context.scene.cursor.location = previous_cursor


def world_bounds(obj):
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector((min(v.x for v in corners), min(v.y for v in corners),
                      min(v.z for v in corners)))
    maximum = Vector((max(v.x for v in corners), max(v.y for v in corners),
                      max(v.z for v in corners)))
    return minimum, maximum


def set_bottom_center_origin(obj):
    minimum, maximum = world_bounds(obj)
    set_origin_world(obj, Vector(((minimum.x + maximum.x) * 0.5,
                                  (minimum.y + maximum.y) * 0.5,
                                  minimum.z)))


def add_bevel(obj, width=BEVEL_WIDTH):
    if width <= 0.0 or obj.type != "MESH":
        return
    modifier = obj.modifiers.new(name="LowPolyBevel", type="BEVEL")
    modifier.width = width
    modifier.segments = 1
    modifier.limit_method = "ANGLE"
    activate_only(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def assign_material(obj, material):
    if obj.type == "MESH":
        obj.data.materials.append(material)


def create_material(name, color, metallic=0.0, roughness=0.8,
                    emission_color=None, emission_strength=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color, 1.0)
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    if emission_color is not None:
        emission_input = shader.inputs.get("Emission Color") or shader.inputs.get("Emission")
        if emission_input:
            emission_input.default_value = (*emission_color, 1.0)
        strength_input = shader.inputs.get("Emission Strength")
        if strength_input:
            strength_input.default_value = emission_strength
    MATERIALS[name] = material
    return material


def create_materials():
    create_material("M_DarkMetal", COLORS["dark_metal"], metallic=0.55, roughness=0.82)
    create_material("M_GrayMetal", COLORS["gray_metal"], metallic=0.45, roughness=0.76)
    create_material("M_DirtyGreen", COLORS["dirty_green"], metallic=0.20, roughness=0.86)
    create_material("M_WarningYellow", COLORS["warning_yellow"], metallic=0.05, roughness=0.72)
    create_material("M_Red", COLORS["warning_red"], metallic=0.05, roughness=0.70,
                    emission_color=COLORS["warning_red"], emission_strength=2.0)
    create_material("M_Black", COLORS["black"], metallic=0.10, roughness=0.92)
    create_material("M_Screen", COLORS["screen_green"], metallic=0.0, roughness=0.45,
                    emission_color=COLORS["screen_green"], emission_strength=3.2)
    create_material("M_Light", COLORS["cold_light"], metallic=0.0, roughness=0.35,
                    emission_color=COLORS["cold_light"], emission_strength=5.0)
    create_material("M_Wood", COLORS["wood"], metallic=0.0, roughness=0.93)


def cube_part(name, location, dimensions, material, collection="Props",
              bevel=BEVEL_WIDTH, rotation=(0.0, 0.0, 0.0), bottom_origin=True):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    obj.dimensions = dimensions
    apply_transforms(obj)
    assign_material(obj, material)
    add_bevel(obj, bevel)
    move_to_collection(obj, collection)
    if bottom_origin:
        set_bottom_center_origin(obj)
    return obj


def cylinder_part(name, location, radius, depth, material, collection="Props",
                  vertices=8, rotation=(0.0, 0.0, 0.0), bevel=0.01,
                  bottom_origin=True):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                       location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    apply_transforms(obj)
    assign_material(obj, material)
    add_bevel(obj, bevel)
    move_to_collection(obj, collection)
    if bottom_origin:
        set_bottom_center_origin(obj)
    return obj


def cylinder_between(name, start, end, radius, material, collection="Pipes",
                     vertices=PIPE_SEGMENTS, bevel=0.008):
    start = Vector(start)
    end = Vector(end)
    direction = end - start
    midpoint = (start + end) * 0.5
    rotation = direction.to_track_quat("Z", "Y").to_euler()
    return cylinder_part(name, midpoint, radius, direction.length, material,
                         collection=collection, vertices=vertices,
                         rotation=rotation, bevel=bevel, bottom_origin=False)


def lowpoly_sphere(name, location, radius, material, collection="Props"):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    apply_transforms(obj)
    assign_material(obj, material)
    move_to_collection(obj, collection)
    set_bottom_center_origin(obj)
    return obj


def join_parts(parts, name, collection, origin="BOTTOM", origin_point=None):
    parts = [part for part in parts if part is not None]
    if not parts:
        raise ValueError(f"No parts supplied for {name}")
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    move_to_collection(obj, collection)
    apply_transforms(obj)
    if origin_point is not None:
        set_origin_world(obj, Vector(origin_point))
    elif origin == "BOTTOM":
        set_bottom_center_origin(obj)
    return obj


def duplicate_object(source, name, location):
    obj = source.copy()
    obj.data = source.data.copy()
    COLLECTIONS[source.users_collection[0].name].objects.link(obj)
    obj.name = name
    obj.location = location
    return obj


def translate_named_objects(names, delta_x, delta_y):
    """Translate a logical asset group without changing any component dimensions."""
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise RuntimeError(f"Cannot relayout missing object: {name}")
        obj.location.x += delta_x
        obj.location.y += delta_y


def move_group_to_scaled_anchor(names, anchor_x, anchor_y):
    translate_named_objects(
        names,
        anchor_x * (LAYOUT_SCALE_X - 1.0),
        anchor_y * (LAYOUT_SCALE_Y - 1.0),
    )


def relayout_for_expanded_room():
    """Spread asset clusters across the larger floor while preserving local layouts."""
    move_group_to_scaled_anchor(("SM_Shelf_A", "SM_Crate_A"), -3.05, 3.69)
    move_group_to_scaled_anchor(("SM_Shelf_B", "SM_Crate_B"), -3.05, 1.845)
    move_group_to_scaled_anchor(("SM_LabDesk", "SM_RetroComputer"), -2.60, -3.55)
    move_group_to_scaled_anchor(("SM_Locker_A", "SM_Locker_B"), 2.99, 3.82)
    move_group_to_scaled_anchor(("SM_Crate_C",), 3.05, -2.65)
    move_group_to_scaled_anchor(
        ("SM_TrashCan", "SM_ScrapMetal_A", "SM_ScrapMetal_B"), 3.15, -3.35
    )
    move_group_to_scaled_anchor(("SM_BrokenBox",), -2.80, 0.40)

    # The pipe assembly stays centered but follows the expanded back wall.
    move_group_to_scaled_anchor(
        ("SM_Pipe_Straight", "SM_Pipe_Corner", "SM_Pipe_Junction"), 0.0, 4.65
    )
    move_group_to_scaled_anchor(("SM_Vent",), 1.65, 4.83)

    # Each light fixture and its Blender preview light move together.
    move_group_to_scaled_anchor(
        ("SM_CeilingLight_A", "LGT_CeilingLight_A"), -1.65, -2.35
    )
    move_group_to_scaled_anchor(
        ("SM_CeilingLight_B", "LGT_CeilingLight_B"), 1.65, 0.0
    )
    move_group_to_scaled_anchor(
        ("SM_CeilingLight_C", "LGT_CeilingLight_C"), -1.65, 2.35
    )

    # Alarm objects preserve their original offset from the relocated door.
    translate_named_objects(
        ("SM_AlarmLight", "LGT_Alarm_Red"),
        DOOR_CENTER_X - 2.15,
        DOOR_Y - (-4.88),
    )


# -----------------------------------------------------------------------------
# Architecture

def create_room():
    dark = MATERIALS["M_DarkMetal"]
    gray = MATERIALS["M_GrayMetal"]
    black = MATERIALS["M_Black"]
    yellow = MATERIALS["M_WarningYellow"]

    cube_part("SM_Floor", (0.0, 0.0, -0.10),
              (ROOM_WIDTH, ROOM_LENGTH, 0.20), dark, "Architecture", 0.0)
    cube_part("SM_Ceiling", (0.0, 0.0, ROOM_HEIGHT + 0.075),
              (ROOM_WIDTH, ROOM_LENGTH, 0.15), dark, "Architecture", 0.0)
    cube_part("SM_Wall_A", (-ROOM_WIDTH * 0.5 - 0.10, 0.0, ROOM_HEIGHT * 0.5),
              (0.20, ROOM_LENGTH, ROOM_HEIGHT), gray, "Architecture", 0.0)
    cube_part("SM_Wall_B", (ROOM_WIDTH * 0.5 + 0.10, 0.0, ROOM_HEIGHT * 0.5),
              (0.20, ROOM_LENGTH, ROOM_HEIGHT), gray, "Architecture", 0.0)
    cube_part("SM_Wall_Back", (0.0, ROOM_LENGTH * 0.5 + 0.10, ROOM_HEIGHT * 0.5),
              (ROOM_WIDTH, 0.20, ROOM_HEIGHT), gray, "Architecture", 0.0)

    door_center_x = DOOR_CENTER_X
    door_width = 1.60
    door_height = 2.60
    door_left = door_center_x - door_width * 0.5
    door_right = door_center_x + door_width * 0.5
    front_y = -ROOM_LENGTH * 0.5 - 0.10
    front_parts = [
        cube_part("FrontWall_Left", ((-ROOM_WIDTH * 0.5 + door_left) * 0.5,
                                     front_y, ROOM_HEIGHT * 0.5),
                  (door_left + ROOM_WIDTH * 0.5, 0.20, ROOM_HEIGHT),
                  gray, "Architecture", 0.0),
        cube_part("FrontWall_Right", ((door_right + ROOM_WIDTH * 0.5) * 0.5,
                                      front_y, ROOM_HEIGHT * 0.5),
                  (ROOM_WIDTH * 0.5 - door_right, 0.20, ROOM_HEIGHT),
                  gray, "Architecture", 0.0),
        cube_part("FrontWall_Header", (door_center_x, front_y,
                                       door_height + (ROOM_HEIGHT - door_height) * 0.5),
                  (door_width, 0.20, ROOM_HEIGHT - door_height),
                  gray, "Architecture", 0.0),
    ]
    join_parts(front_parts, "SM_Wall_Front", "Architecture",
               origin_point=(-ROOM_WIDTH * 0.5, -ROOM_LENGTH * 0.5 - 0.20, 0.0))

    # Sparse support beams: enough to sell the industrial construction.
    support_parts = []
    for x in (-ROOM_WIDTH * 0.5 + 0.20, ROOM_WIDTH * 0.5 - 0.20):
        support_parts.append(cube_part("WallSupport", (x, ROOM_LENGTH * 0.5 - 0.14, 2.0),
                                       (0.16, 0.18, 4.0), dark,
                                       "Architecture", 0.008))
    for x in (-2.0 * LAYOUT_SCALE_X, 0.0, 2.0 * LAYOUT_SCALE_X):
        support_parts.append(cube_part("CeilingRib", (x, 0.0, 3.91),
                                       (0.12, ROOM_LENGTH - 0.30, 0.14), dark,
                                       "Architecture", 0.008))
    join_parts(support_parts, "SM_Room_Supports", "Architecture")

    # Metal floor strips and a simple drain.
    strip_parts = []
    for y in (-2.2 * LAYOUT_SCALE_Y, 2.2 * LAYOUT_SCALE_Y):
        strip_parts.append(cube_part("FloorStrip", (0.0, y, 0.018),
                                     (ROOM_WIDTH - 0.35, 0.055, 0.035), gray,
                                     "Architecture", 0.004))
    join_parts(strip_parts, "SM_Floor_MetalStrips", "Architecture")

    drain_x = -2.20 * LAYOUT_SCALE_X
    drain_y = -0.35 * LAYOUT_SCALE_Y
    drain_parts = [cube_part("DrainBase", (drain_x, drain_y, 0.022),
                             (0.85, 0.55, 0.04), black, "Architecture", 0.005)]
    for offset_x in (-0.30, -0.15, 0.0, 0.15, 0.30):
        drain_parts.append(cube_part("DrainBar", (drain_x + offset_x, drain_y, 0.052),
                                     (0.045, 0.48, 0.035), gray,
                                     "Architecture", 0.003))
    join_parts(drain_parts, "SM_Drain", "Architecture")

    warning_parts = []
    for x, y, dx, dy in ((0.0, -1.48, 3.0, 0.09), (0.0, 1.48, 3.0, 0.09),
                         (-1.48, 0.0, 0.09, 3.0), (1.48, 0.0, 0.09, 3.0)):
        warning_parts.append(cube_part("WarningBorder", (x, y, 0.035),
                                       (dx, dy, 0.035), yellow,
                                       "Architecture", 0.003))
    join_parts(warning_parts, "SM_WarningArea", "Architecture")


def create_door():
    dark = MATERIALS["M_DarkMetal"]
    gray = MATERIALS["M_GrayMetal"]
    yellow = MATERIALS["M_WarningYellow"]
    black = MATERIALS["M_Black"]
    screen = MATERIALS["M_Screen"]

    x = DOOR_CENTER_X
    y = DOOR_Y
    parts = [cube_part("DoorSlab", (x, y, 1.30), (1.54, 0.15, 2.56),
                       dark, "Architecture", 0.025)]
    # Recessed center panel and strong yellow edge language.
    parts.extend([
        cube_part("DoorInset", (x, y + 0.085, 1.25), (1.18, 0.045, 1.75),
                  gray, "Architecture", 0.012),
        cube_part("DoorYellowL", (x - 0.68, y + 0.10, 1.30), (0.10, 0.045, 2.36),
                  yellow, "Architecture", 0.005),
        cube_part("DoorYellowR", (x + 0.68, y + 0.10, 1.30), (0.10, 0.045, 2.36),
                  yellow, "Architecture", 0.005),
        cube_part("DoorYellowTop", (x, y + 0.10, 2.43), (1.28, 0.045, 0.10),
                  yellow, "Architecture", 0.005),
        cube_part("WindowFrame", (x, y + 0.125, 1.80), (0.68, 0.045, 0.48),
                  black, "Architecture", 0.008),
        cube_part("WindowGlass", (x, y + 0.153, 1.80), (0.52, 0.025, 0.32),
                  screen, "Architecture", 0.004),
    ])
    join_parts(parts, "SM_Door_Industrial", "Architecture",
               origin_point=(x - 0.80, y, 0.0))

    panel_parts = [
        cube_part("AccessBase", (x + 1.13, y + 0.04, 1.30), (0.28, 0.16, 0.48),
                  black, "Architecture", 0.015),
        cube_part("AccessFace", (x + 1.13, y + 0.14, 1.35), (0.18, 0.04, 0.18),
                  screen, "Architecture", 0.006),
        cylinder_part("AccessButton", (x + 1.13, y + 0.18, 1.15), 0.055, 0.035,
                      MATERIALS["M_Red"], "Architecture", 8,
                      rotation=(math.radians(90), 0.0, 0.0), bevel=0.003),
    ]
    join_parts(panel_parts, "SM_DoorAccessPanel", "Architecture")


# -----------------------------------------------------------------------------
# Props

def create_shelf(name, location, slight_offset=0.0):
    x, y, z = location
    dark = MATERIALS["M_DarkMetal"]
    green = MATERIALS["M_DirtyGreen"]
    parts = []
    width, depth, height = 1.45, 0.58, 2.55
    for px in (-width * 0.5, width * 0.5):
        for py in (-depth * 0.5, depth * 0.5):
            parts.append(cube_part("ShelfPost", (x + px, y + py, z + height * 0.5),
                                   (0.075, 0.075, height), dark, "Props", 0.007))
    for index, shelf_z in enumerate((0.18, 0.92, 1.66, 2.40)):
        parts.append(cube_part("ShelfBoard", (x + (slight_offset if index == 2 else 0.0),
                                               y, z + shelf_z),
                               (width + 0.12, depth + 0.10, 0.095), green,
                               "Props", 0.009))
    return join_parts(parts, name, "Props")


def create_shelves():
    create_shelf("SM_Shelf_A", (-3.05, 3.70, 0.0), 0.02)
    create_shelf("SM_Shelf_B", (-3.05, 1.85, 0.0), -0.025)


def create_crate(name, location, size, variant=0, collection="Props"):
    x, y, z = location
    sx, sy, sz = size
    wood = MATERIALS["M_Wood"]
    dark = MATERIALS["M_DarkMetal"]
    yellow = MATERIALS["M_WarningYellow"]
    body_mat = wood if variant != 2 else MATERIALS["M_DirtyGreen"]
    frame_mat = dark if variant != 1 else yellow
    parts = [cube_part("CrateBody", (x, y, z + sz * 0.5),
                       (sx, sy, sz), body_mat, collection, 0.018)]
    rail = 0.055
    for px in (-sx * 0.5 + rail * 0.5, sx * 0.5 - rail * 0.5):
        parts.append(cube_part("CrateRail", (x + px, y, z + sz * 0.5),
                               (rail, sy + 0.025, sz + 0.03), frame_mat,
                               collection, 0.004))
    for py in (-sy * 0.5 + rail * 0.5, sy * 0.5 - rail * 0.5):
        parts.append(cube_part("CrateRail", (x, y + py, z + sz - rail * 0.5),
                               (sx + 0.025, rail, rail), frame_mat,
                               collection, 0.004))
    parts.append(cube_part("CrateLid", (x, y, z + sz + 0.035),
                           (sx + 0.04, sy + 0.04, 0.07), frame_mat,
                           collection, 0.006))
    return join_parts(parts, name, collection)


def create_crates():
    create_crate("SM_Crate_A", (-3.05, 3.68, 0.28), (0.70, 0.45, 0.52), 0)
    create_crate("SM_Crate_B", (-3.05, 1.84, 1.02), (0.78, 0.46, 0.54), 1)
    create_crate("SM_Crate_C", (3.05, -2.65, 0.0), (0.92, 0.68, 0.72), 2)


def create_lab_desk():
    x, y = -2.60, -3.55
    dark = MATERIALS["M_DarkMetal"]
    green = MATERIALS["M_DirtyGreen"]
    gray = MATERIALS["M_GrayMetal"]
    parts = [cube_part("DeskTop", (x, y, 0.90), (2.00, 0.80, 0.12),
                       green, "Props", 0.018)]
    for px in (-0.86, 0.86):
        for py in (-0.29, 0.29):
            parts.append(cube_part("DeskLeg", (x + px, y + py, 0.44),
                                   (0.11, 0.11, 0.88), dark, "Props", 0.008))
    parts.extend([
        cube_part("DeskBrace", (x, y - 0.32, 0.48), (1.74, 0.08, 0.12),
                  dark, "Props", 0.008),
        cube_part("KeyboardSlab", (x + 0.25, y + 0.20, 1.00), (0.70, 0.25, 0.055),
                  gray, "Props", 0.008),
        cube_part("ControlBox", (x + 0.72, y - 0.15, 1.08), (0.32, 0.30, 0.28),
                  dark, "Props", 0.012),
    ])
    join_parts(parts, "SM_LabDesk", "Props")


def create_retro_computer():
    x, y = -2.90, -3.47
    dark = MATERIALS["M_DarkMetal"]
    gray = MATERIALS["M_GrayMetal"]
    screen = MATERIALS["M_Screen"]
    parts = [
        cube_part("CRTBody", (x, y, 1.34), (0.72, 0.58, 0.68),
                  gray, "Props", 0.035),
        cube_part("CRTBezel", (x, y + 0.307, 1.39), (0.61, 0.045, 0.49),
                  dark, "Props", 0.018),
        cube_part("CRTScreen", (x, y + 0.337, 1.39), (0.47, 0.025, 0.34),
                  screen, "Props", 0.025),
        cube_part("CRTStand", (x, y - 0.02, 0.99), (0.38, 0.34, 0.12),
                  dark, "Props", 0.012),
    ]
    # A few large, readable controls rather than a textured UI.
    for offset in (-0.10, 0.10):
        parts.append(cylinder_part("CRTKnob", (x + offset, y + 0.337, 1.11),
                                   0.035, 0.025, MATERIALS["M_WarningYellow"],
                                   "Props", 8, rotation=(math.radians(90), 0.0, 0.0),
                                   bevel=0.002))
    join_parts(parts, "SM_RetroComputer", "Props")


def create_locker(name, location, dent=0.0):
    x, y, z = location
    green = MATERIALS["M_DirtyGreen"]
    dark = MATERIALS["M_DarkMetal"]
    gray = MATERIALS["M_GrayMetal"]
    parts = [
        cube_part("LockerBody", (x, y, z + 1.10), (0.72, 0.62, 2.20),
                  green, "Props", 0.018),
        cube_part("LockerDoor", (x + dent, y - 0.326, z + 1.10), (0.62, 0.035, 2.04),
                  green, "Props", 0.008),
        cube_part("LockerHandle", (x + 0.20, y - 0.365, z + 1.08), (0.07, 0.055, 0.32),
                  gray, "Props", 0.006),
        cube_part("LockerToe", (x, y - 0.015, z + 0.08), (0.58, 0.50, 0.16),
                  dark, "Props", 0.006),
    ]
    for slot_z in (1.72, 1.84, 1.96):
        parts.append(cube_part("LockerVent", (x, y - 0.354, z + slot_z),
                               (0.34, 0.035, 0.035), dark, "Props", 0.002))
    return join_parts(parts, name, "Props")


def create_lockers():
    create_locker("SM_Locker_A", (3.42, 3.82, 0.0), 0.0)
    create_locker("SM_Locker_B", (2.56, 3.82, 0.0), -0.018)


def create_trash():
    dark = MATERIALS["M_DarkMetal"]
    gray = MATERIALS["M_GrayMetal"]
    black = MATERIALS["M_Black"]

    trash_parts = [
        cylinder_part("TrashBody", (3.45, -3.75, 0.35), 0.31, 0.70,
                      dark, "Props", 8, bevel=0.01),
        cylinder_part("TrashRim", (3.45, -3.75, 0.72), 0.35, 0.07,
                      gray, "Props", 8, bevel=0.006),
        cylinder_part("TrashHole", (3.45, -3.75, 0.765), 0.25, 0.03,
                      black, "Props", 8, bevel=0.002),
    ]
    join_parts(trash_parts, "SM_TrashCan", "Props")

    scrap_a = [
        cube_part("ScrapPlate", (2.65, -3.60, 0.075), (0.58, 0.18, 0.08),
                  gray, "Props", 0.004, rotation=(0.0, 0.0, math.radians(18))),
        cylinder_part("ScrapBolt", (2.78, -3.52, 0.14), 0.07, 0.12,
                      dark, "Props", 6, bevel=0.002),
    ]
    join_parts(scrap_a, "SM_ScrapMetal_A", "Props")

    scrap_b = [
        cylinder_between("ScrapPipe", (2.72, -3.10, 0.08), (3.15, -2.98, 0.22),
                         0.065, dark, "Props", 6, 0.003),
        cube_part("ScrapBracket", (3.13, -2.98, 0.14), (0.18, 0.20, 0.10),
                  gray, "Props", 0.004, rotation=(0.0, 0.0, math.radians(-12))),
    ]
    join_parts(scrap_b, "SM_ScrapMetal_B", "Props")

    broken = [
        cube_part("BrokenBody", (-2.80, 0.40, 0.24), (0.70, 0.48, 0.42),
                  MATERIALS["M_Wood"], "Props", 0.012,
                  rotation=(0.0, 0.0, math.radians(-8))),
        cube_part("BrokenLid", (-2.66, 0.38, 0.57), (0.62, 0.43, 0.07),
                  dark, "Props", 0.005,
                  rotation=(math.radians(8), 0.0, math.radians(10))),
    ]
    join_parts(broken, "SM_BrokenBox", "Props")


# -----------------------------------------------------------------------------
# Pipes, vent and lighting

def create_pipes():
    dark = MATERIALS["M_DarkMetal"]
    gray = MATERIALS["M_GrayMetal"]

    straight_parts = [
        cylinder_between("PipeMain", (-3.60, 4.65, 3.38), (2.80, 4.65, 3.38),
                         PIPE_RADIUS, gray),
    ]
    for x in (-2.60, -0.60, 1.40):
        straight_parts.append(cylinder_between("PipeCollar", (x - 0.045, 4.65, 3.38),
                                               (x + 0.045, 4.65, 3.38),
                                               PIPE_RADIUS * 1.25, dark,
                                               vertices=PIPE_SEGMENTS, bevel=0.004))
    join_parts(straight_parts, "SM_Pipe_Straight", "Pipes")

    # Chunky two-segment elbow; the faceted joint is intentional low-poly style.
    corner_parts = [
        cylinder_between("CornerHorizontal", (2.80, 4.65, 3.38), (3.35, 4.65, 3.38),
                         PIPE_RADIUS, gray),
        cylinder_between("CornerVertical", (3.35, 4.65, 3.38), (3.35, 4.65, 2.74),
                         PIPE_RADIUS, gray),
        lowpoly_sphere("CornerJoint", (3.35, 4.65, 3.38), PIPE_RADIUS * 1.12,
                       gray, "Pipes"),
    ]
    join_parts(corner_parts, "SM_Pipe_Corner", "Pipes")

    junction_parts = [
        cylinder_between("JunctionVertical", (-2.75, 4.65, 3.38),
                         (-2.75, 4.65, 2.72), PIPE_RADIUS * 0.82, dark),
        cylinder_between("JunctionBranch", (-2.75, 4.65, 2.90),
                         (-3.58, 4.65, 2.90), PIPE_RADIUS * 0.82, dark),
        lowpoly_sphere("JunctionHub", (-2.75, 4.65, 2.90), PIPE_RADIUS,
                       dark, "Pipes"),
    ]
    join_parts(junction_parts, "SM_Pipe_Junction", "Pipes")


def create_vent():
    x, y, z = 1.65, 4.83, 2.50
    dark = MATERIALS["M_DarkMetal"]
    gray = MATERIALS["M_GrayMetal"]
    parts = [
        cube_part("VentBack", (x, y, z), (1.20, 0.10, 0.84), dark,
                  "Pipes", 0.012),
        cube_part("VentTop", (x, y - 0.065, z + 0.39), (1.30, 0.10, 0.08), gray,
                  "Pipes", 0.005),
        cube_part("VentBottom", (x, y - 0.065, z - 0.39), (1.30, 0.10, 0.08), gray,
                  "Pipes", 0.005),
        cube_part("VentLeft", (x - 0.61, y - 0.065, z), (0.08, 0.10, 0.72), gray,
                  "Pipes", 0.005),
        cube_part("VentRight", (x + 0.61, y - 0.065, z), (0.08, 0.10, 0.72), gray,
                  "Pipes", 0.005),
    ]
    for offset in (-0.24, -0.12, 0.0, 0.12, 0.24):
        parts.append(cube_part("VentSlat", (x, y - 0.13, z + offset),
                               (1.05, 0.08, 0.055), gray, "Pipes", 0.003,
                               rotation=(math.radians(-10), 0.0, 0.0)))
    join_parts(parts, "SM_Vent", "Pipes")


def create_ceiling_light(name, location):
    x, y, z = location
    dark = MATERIALS["M_DarkMetal"]
    light_mat = MATERIALS["M_Light"]
    parts = [
        cube_part("LightHousing", (x, y, z), (1.65, 0.42, 0.13),
                  dark, "Lights", 0.012),
        cube_part("LightStrip", (x, y, z - 0.085), (1.38, 0.24, 0.055),
                  light_mat, "Lights", 0.008),
    ]
    fixture = join_parts(parts, name, "Lights")

    data = bpy.data.lights.new(name.replace("SM_", "LGT_"), type="AREA")
    data.energy = 480.0
    data.color = COLORS["cold_light"]
    data.shape = "RECTANGLE"
    data.size = 1.45
    data.size_y = 0.36
    light_obj = bpy.data.objects.new(data.name, data)
    COLLECTIONS["Lights"].objects.link(light_obj)
    light_obj.location = (x, y, z - 0.15)
    return fixture


def create_ceiling_lights():
    create_ceiling_light("SM_CeilingLight_A", (-1.65, -2.35, 3.78))
    create_ceiling_light("SM_CeilingLight_B", (1.65, 0.00, 3.78))
    create_ceiling_light("SM_CeilingLight_C", (-1.65, 2.35, 3.78))


def create_alarm_light():
    red = MATERIALS["M_Red"]
    dark = MATERIALS["M_DarkMetal"]
    parts = [
        cube_part("AlarmBase", (3.35, -4.79, 2.72), (0.28, 0.16, 0.30),
                  dark, "Lights", 0.014),
        lowpoly_sphere("AlarmLens", (3.35, -4.66, 2.74), 0.13, red, "Lights"),
    ]
    join_parts(parts, "SM_AlarmLight", "Lights")

    data = bpy.data.lights.new("LGT_Alarm_Red", type="POINT")
    data.energy = 85.0
    data.color = (1.0, 0.02, 0.01)
    data.shadow_soft_size = 0.55
    light_obj = bpy.data.objects.new("LGT_Alarm_Red", data)
    COLLECTIONS["Lights"].objects.link(light_obj)
    light_obj.location = (3.18, -4.30, 2.68)


def create_test_loot_crate():
    x, y, z = 0.0, 0.0, 0.0
    yellow = MATERIALS["M_WarningYellow"]
    dark = MATERIALS["M_DarkMetal"]
    red = MATERIALS["M_Red"]
    parts = [
        cube_part("LootBody", (x, y, z + 0.50), (1.0, 1.0, 1.0),
                  yellow, "Gameplay", 0.035),
        cube_part("LootInset", (x, y - 0.515, z + 0.52), (0.66, 0.035, 0.50),
                  dark, "Gameplay", 0.012),
        cube_part("LootTop", (x, y, z + 1.02), (1.08, 1.08, 0.12),
                  dark, "Gameplay", 0.012),
    ]
    for px in (-0.43, 0.43):
        parts.append(cube_part("LootRail", (x + px, y, z + 0.50),
                               (0.09, 1.05, 0.90), dark,
                               "Gameplay", 0.006))
    parts.append(lowpoly_sphere("LootIndicator", (x, y - 0.56, z + 0.68),
                                0.075, red, "Gameplay"))
    join_parts(parts, "SM_TestLootCrate", "Gameplay")


# -----------------------------------------------------------------------------
# Scene settings, validation and output

def point_object_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_preview_lighting():
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.012, 0.016, 0.020, 1.0)
    background.inputs["Strength"].default_value = 0.12

    fill_data = bpy.data.lights.new("LGT_WeakFill", type="POINT")
    fill_data.energy = 180.0
    fill_data.color = (0.42, 0.53, 0.60)
    fill_data.shadow_soft_size = 2.2
    fill_obj = bpy.data.objects.new("LGT_WeakFill", fill_data)
    COLLECTIONS["Lights"].objects.link(fill_obj)
    fill_obj.location = (0.0, -0.8, 2.25)

    camera_data = bpy.data.cameras.new("CAM_Preview")
    camera = bpy.data.objects.new("CAM_Preview", camera_data)
    COLLECTIONS["Lights"].objects.link(camera)
    camera.location = (0.0, ROOM_LENGTH * 1.30, 10.50)
    camera_data.lens = 28.0
    camera_data.sensor_width = 36.0
    point_object_at(camera, (0.0, -0.70, 1.20))
    scene.camera = camera

    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = PREVIEW_PATH.as_posix()
    scene.render.film_transparent = False

    # Neutral color management keeps the palette readable and inexpensive-looking.
    available_looks = {
        item.identifier
        for item in scene.view_settings.bl_rna.properties["look"].enum_items
    }
    preferred_look = "AgX - Medium High Contrast"
    scene.view_settings.look = preferred_look if preferred_look in available_looks else "None"


def apply_all_mesh_transforms():
    for obj in list(bpy.context.scene.objects):
        if obj.type == "MESH":
            apply_transforms(obj)


def scene_statistics():
    objects = list(bpy.context.scene.objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    lights = [obj for obj in objects if obj.type == "LIGHT"]
    triangles = 0
    for obj in meshes:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
    return {
        "objects": len(objects),
        "meshes": len(meshes),
        "materials": len(bpy.data.materials),
        "triangles": triangles,
        "lights": len(lights),
    }


def validate_scene():
    required = {
        "SM_Floor", "SM_Ceiling", "SM_Wall_A", "SM_Wall_B",
        "SM_Wall_Back", "SM_Wall_Front", "SM_Door_Industrial",
        "SM_Shelf_A", "SM_Shelf_B", "SM_LabDesk", "SM_RetroComputer",
        "SM_Locker_A", "SM_Locker_B", "SM_Crate_A", "SM_Crate_B",
        "SM_Crate_C", "SM_Pipe_Straight", "SM_Pipe_Corner",
        "SM_Pipe_Junction", "SM_Vent", "SM_TrashCan",
        "SM_CeilingLight_A", "SM_CeilingLight_B", "SM_AlarmLight",
        "SM_TestLootCrate",
    }
    missing = sorted(required - set(bpy.data.objects.keys()))
    if missing:
        raise RuntimeError(f"Missing required objects: {missing}")

    expected_collections = {"LowPolyLab", "Architecture", "Props", "Pipes",
                            "Lights", "Gameplay"}
    missing_collections = sorted(expected_collections - set(bpy.data.collections.keys()))
    if missing_collections:
        raise RuntimeError(f"Missing collections: {missing_collections}")

    invalid_transforms = []
    mismatched_mesh_names = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        if obj.data.name != obj.name:
            mismatched_mesh_names.append(f"{obj.name} -> {obj.data.name}")
        if any(abs(value - 1.0) > 1e-5 for value in obj.scale):
            invalid_transforms.append(f"{obj.name}: scale")
        if any(abs(value) > 1e-5 for value in obj.rotation_euler):
            invalid_transforms.append(f"{obj.name}: rotation")
    if invalid_transforms:
        raise RuntimeError(f"Unapplied mesh transforms: {invalid_transforms}")
    if mismatched_mesh_names:
        raise RuntimeError(f"Mesh datablock names do not match objects: {mismatched_mesh_names}")

    stats = scene_statistics()
    if stats["materials"] >= 10:
        raise RuntimeError(f"Material count must be < 10, got {stats['materials']}")
    if stats["triangles"] >= 100_000:
        raise RuntimeError(f"Triangle count must be < 100,000, got {stats['triangles']}")

    expected_dimensions = {
        "SM_Floor": (ROOM_WIDTH, ROOM_LENGTH, 0.20),
        "SM_Door_Industrial": (1.54, 0.2405, 2.56),
        "SM_LabDesk": (2.00, 0.80, 1.22),
        "SM_RetroComputer": (0.72, 0.6395, 0.75),
        "SM_Shelf_A": (1.59, 0.68, 2.55),
        "SM_Locker_A": (0.72, 0.7025, 2.20),
        "SM_Crate_A": (0.74, 0.49, 0.605),
        "SM_TestLootCrate": (1.08, 1.163798, 1.08),
        "SM_Pipe_Straight": (6.40, 0.296939, 0.296939),
    }
    for name, expected in expected_dimensions.items():
        actual = bpy.data.objects[name].dimensions
        if any(abs(actual[index] - expected[index]) > 1e-4 for index in range(3)):
            raise RuntimeError(
                f"Unexpected dimensions for {name}: {tuple(actual)} != {expected}"
            )

    door = bpy.data.objects["SM_Door_Industrial"]
    expected_hinge = Vector((DOOR_CENTER_X - 0.80, DOOR_Y, 0.0))
    if (door.location - expected_hinge).length > 1e-4:
        raise RuntimeError(f"Door origin is not at hinge: {tuple(door.location)}")
    return stats


def save_and_export():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = PREVIEW_PATH.as_posix()
    # A temporary cutaway view makes the whole room readable in one validation image.
    cutaway_objects = [
        bpy.data.objects["SM_Ceiling"],
        bpy.data.objects["SM_Wall_Back"],
        bpy.data.objects["SM_Room_Supports"],
    ]
    for obj in cutaway_objects:
        obj.hide_render = True
    bpy.ops.render.render(write_still=True)
    for obj in cutaway_objects:
        obj.hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH.as_posix(), check_existing=False)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=FBX_PATH.as_posix(),
        check_existing=False,
        use_selection=True,
        object_types={"MESH"},
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        use_space_transform=True,
        bake_space_transform=True,
        axis_forward="-Y",
        axis_up="Z",
        use_mesh_modifiers=True,
        mesh_smooth_type="FACE",
        use_triangles=False,
        add_leaf_bones=False,
        path_mode="AUTO",
        embed_textures=False,
    )


def main():
    clear_scene()
    create_collections()
    create_materials()

    create_room()
    create_door()
    create_shelves()
    create_crates()
    create_lab_desk()
    create_retro_computer()
    create_lockers()
    create_trash()
    create_pipes()
    create_vent()
    create_ceiling_lights()
    create_alarm_light()
    create_test_loot_crate()
    relayout_for_expanded_room()
    setup_preview_lighting()

    apply_all_mesh_transforms()
    stats = validate_scene()
    save_and_export()

    print("\n=== Low Poly Lab Generation Complete ===\n")
    print(f"Objects:   {stats['objects']}")
    print(f"Meshes:    {stats['meshes']}")
    print(f"Materials: {stats['materials']}")
    print(f"Triangles: {stats['triangles']}")
    print(f"Lights:    {stats['lights']}")
    print(f"\nBlend:\n{BLEND_PATH}")
    print(f"\nFBX:\n{FBX_PATH}")
    print(f"\nPreview:\n{PREVIEW_PATH}\n")


if __name__ == "__main__":
    main()
