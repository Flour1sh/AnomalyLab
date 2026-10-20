"""Generate an original low-poly industrial-horror worker in Blender.

Run with:
    blender --background --factory-startup --python generate_worker.py

The script uses Blender's bundled bpy API only. It creates a segmented,
rig-ready A-pose character, renders a preview, saves the .blend file, validates
the prototype constraints, and exports a mesh-only UE5-oriented FBX.
"""

from pathlib import Path
import math

import bpy
from mathutils import Vector


# -----------------------------------------------------------------------------
# Main parameters

CHARACTER_HEIGHT = 1.80
BASE_CHARACTER_HEIGHT = 1.80
HEAD_SCALE = 1.05
TORSO_WIDTH = 0.52
TORSO_DEPTH = 0.28
ARM_LENGTH_SCALE = 1.05
HAND_SCALE = 1.15
LEG_THICKNESS = 0.15
BOOT_SCALE = 1.15
CYLINDER_SEGMENTS = 8
BEVEL_WIDTH = 0.01

OUTPUT_DIR = Path(__file__).resolve().parent
BLEND_PATH = OUTPUT_DIR / "low_poly_worker.blend"
FBX_PATH = OUTPUT_DIR / "low_poly_worker.fbx"
PREVIEW_PATH = OUTPUT_DIR / "low_poly_worker_preview.png"
BACK_PREVIEW_PATH = OUTPUT_DIR / "low_poly_worker_back_preview.png"

COLORS = {
    "suit": (0.58, 0.25, 0.055),
    "dark": (0.045, 0.055, 0.060),
    "helmet": (0.105, 0.125, 0.125),
    "visor": (0.012, 0.042, 0.043),
    "metal": (0.20, 0.225, 0.23),
    "warning": (0.90, 0.57, 0.025),
}

COLLECTIONS = {}
MATERIALS = {}


# -----------------------------------------------------------------------------
# General helpers

def clear_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            datablocks.remove(datablock)


def setup_units():
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0


def create_collections():
    root = bpy.data.collections.new("LowPolyWorker")
    bpy.context.scene.collection.children.link(root)
    COLLECTIONS["root"] = root
    for name in ("Body", "Equipment", "Rig", "Preview"):
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


def mark_exportable(obj):
    obj["ue_export"] = True
    return obj


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
        emission = shader.inputs.get("Emission Color") or shader.inputs.get("Emission")
        if emission:
            emission.default_value = (*emission_color, 1.0)
        strength = shader.inputs.get("Emission Strength")
        if strength:
            strength.default_value = emission_strength
    MATERIALS[name] = material
    return material


def create_materials():
    create_material("M_Suit", COLORS["suit"], roughness=0.93)
    create_material("M_Dark", COLORS["dark"], metallic=0.08, roughness=0.86)
    create_material("M_Helmet", COLORS["helmet"], metallic=0.28, roughness=0.68)
    create_material(
        "M_Visor",
        COLORS["visor"],
        metallic=0.35,
        roughness=0.24,
        emission_color=(0.015, 0.10, 0.085),
        emission_strength=0.35,
    )
    create_material("M_Metal", COLORS["metal"], metallic=0.62, roughness=0.74)
    create_material("M_Warning", COLORS["warning"], metallic=0.05, roughness=0.70)


def assign_material(obj, material):
    if obj.type == "MESH":
        obj.data.materials.append(material)


def add_bevel(obj, width=BEVEL_WIDTH, segments=1):
    if width <= 0.0 or obj.type != "MESH":
        return
    modifier = obj.modifiers.new(name="LowPolyBevel", type="BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    activate_only(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def shade_flat(obj):
    if obj.type != "MESH":
        return
    for polygon in obj.data.polygons:
        polygon.use_smooth = False


def cube_part(name, location, dimensions, material, collection="Body",
              bevel=BEVEL_WIDTH, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    obj.dimensions = dimensions
    apply_transforms(obj)
    assign_material(obj, material)
    add_bevel(obj, bevel)
    shade_flat(obj)
    move_to_collection(obj, collection)
    return obj


def cylinder_part(name, location, radius, depth, material, collection="Body",
                  vertices=CYLINDER_SEGMENTS, rotation=(0.0, 0.0, 0.0),
                  bevel=0.006):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    apply_transforms(obj)
    assign_material(obj, material)
    add_bevel(obj, bevel)
    shade_flat(obj)
    move_to_collection(obj, collection)
    return obj


def cone_between(name, start, end, radius_start, radius_end, material,
                 collection="Body", vertices=CYLINDER_SEGMENTS, bevel=0.005):
    start = Vector(start)
    end = Vector(end)
    direction = end - start
    midpoint = (start + end) * 0.5
    rotation = direction.to_track_quat("Z", "Y").to_euler()
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius_start,
        radius2=radius_end,
        depth=direction.length,
        location=midpoint,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    apply_transforms(obj)
    assign_material(obj, material)
    add_bevel(obj, bevel)
    shade_flat(obj)
    move_to_collection(obj, collection)
    return obj


def lowpoly_sphere(name, location, radius, material, collection="Body",
                   subdivisions=2, scale=(1.0, 1.0, 1.0)):
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=subdivisions,
        radius=radius,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    obj.scale = scale
    apply_transforms(obj)
    assign_material(obj, material)
    shade_flat(obj)
    move_to_collection(obj, collection)
    return obj


def tapered_box(name, location, height, lower_width, upper_width,
                lower_depth, upper_depth, material, collection="Body",
                bevel=BEVEL_WIDTH):
    x, y, z = location
    z0 = z - height * 0.5
    z1 = z + height * 0.5
    vertices = [
        (-lower_width * 0.5, -lower_depth * 0.5, z0),
        (lower_width * 0.5, -lower_depth * 0.5, z0),
        (lower_width * 0.5, lower_depth * 0.5, z0),
        (-lower_width * 0.5, lower_depth * 0.5, z0),
        (-upper_width * 0.5, -upper_depth * 0.5, z1),
        (upper_width * 0.5, -upper_depth * 0.5, z1),
        (upper_width * 0.5, upper_depth * 0.5, z1),
        (-upper_width * 0.5, upper_depth * 0.5, z1),
    ]
    vertices = [(vx + x, vy + y, vz) for vx, vy, vz in vertices]
    faces = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    COLLECTIONS[collection].objects.link(obj)
    assign_material(obj, material)
    add_bevel(obj, bevel)
    shade_flat(obj)
    return obj


def trapezoid_prism(name, center, top_width, bottom_width, height, depth,
                    material, collection="Body", bevel=0.004):
    x, y, z = center
    z0 = z - height * 0.5
    z1 = z + height * 0.5
    yf = y - depth * 0.5
    yb = y + depth * 0.5
    vertices = [
        (x - bottom_width * 0.5, yf, z0),
        (x + bottom_width * 0.5, yf, z0),
        (x - top_width * 0.5, yf, z1),
        (x + top_width * 0.5, yf, z1),
        (x - bottom_width * 0.5, yb, z0),
        (x + bottom_width * 0.5, yb, z0),
        (x - top_width * 0.5, yb, z1),
        (x + top_width * 0.5, yb, z1),
    ]
    faces = [
        (0, 1, 3, 2),
        (4, 6, 7, 5),
        (0, 4, 5, 1),
        (2, 3, 7, 6),
        (0, 2, 6, 4),
        (1, 5, 7, 3),
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    COLLECTIONS[collection].objects.link(obj)
    assign_material(obj, material)
    add_bevel(obj, bevel)
    shade_flat(obj)
    return obj


def join_parts(parts, name, collection, origin_point=None, exportable=True):
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
    shade_flat(obj)
    if origin_point is not None:
        set_origin_world(obj, Vector(origin_point))
    if exportable:
        mark_exportable(obj)
    return obj


def direction_rotation(start, end):
    direction = Vector(end) - Vector(start)
    return direction.to_track_quat("Z", "Y").to_euler()


def world_bounds(objects):
    corners = []
    for obj in objects:
        corners.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    minimum = Vector((
        min(point.x for point in corners),
        min(point.y for point in corners),
        min(point.z for point in corners),
    ))
    maximum = Vector((
        max(point.x for point in corners),
        max(point.y for point in corners),
        max(point.z for point in corners),
    ))
    return minimum, maximum


# -----------------------------------------------------------------------------
# Character construction

def create_head():
    helmet = MATERIALS["M_Helmet"]
    dark = MATERIALS["M_Dark"]
    visor = MATERIALS["M_Visor"]
    warning = MATERIALS["M_Warning"]
    metal = MATERIALS["M_Metal"]

    center = (0.0, 0.0, 1.585)
    shell_radius = 0.205 * HEAD_SCALE
    parts = [
        lowpoly_sphere(
            "HelmetShell",
            center,
            shell_radius,
            helmet,
            subdivisions=3,
            scale=(1.03, 0.92, 1.0),
        ),
        trapezoid_prism(
            "Visor",
            (0.0, -0.197, 1.595),
            0.335,
            0.285,
            0.165,
            0.030,
            visor,
            bevel=0.008,
        ),
        cube_part(
            "HelmetBrow",
            (0.0, -0.195, 1.705),
            (0.355, 0.045, 0.045),
            dark,
            bevel=0.008,
        ),
        cube_part(
            "HelmetChin",
            (0.0, -0.176, 1.470),
            (0.305, 0.075, 0.065),
            dark,
            bevel=0.010,
        ),
        cube_part(
            "HelmetTopStripe",
            (0.0, -0.035, 1.785),
            (0.075, 0.235, 0.025),
            warning,
            bevel=0.004,
        ),
    ]
    for side in (-1.0, 1.0):
        parts.append(
            cylinder_part(
                "HelmetEarCap",
                (side * 0.210, 0.0, 1.585),
                0.065,
                0.032,
                metal,
                vertices=8,
                rotation=(0.0, math.radians(90), 0.0),
                bevel=0.004,
            )
        )
        parts.append(
            cube_part(
                "HelmetJawRail",
                (side * 0.168, -0.105, 1.485),
                (0.045, 0.115, 0.090),
                helmet,
                bevel=0.007,
            )
        )
    return join_parts(parts, "SM_Head", "Body", origin_point=center)


def create_neck():
    parts = [
        cylinder_part(
            "NeckSeal",
            (0.0, 0.0, 1.425),
            0.145,
            0.105,
            MATERIALS["M_Dark"],
            vertices=8,
            bevel=0.006,
        ),
        cylinder_part(
            "NeckLock",
            (0.0, 0.0, 1.446),
            0.165,
            0.040,
            MATERIALS["M_Metal"],
            vertices=8,
            bevel=0.004,
        ),
    ]
    return join_parts(parts, "SM_Neck", "Body", origin_point=(0.0, 0.0, 1.40))


def create_torso():
    suit = MATERIALS["M_Suit"]
    dark = MATERIALS["M_Dark"]
    metal = MATERIALS["M_Metal"]
    warning = MATERIALS["M_Warning"]
    parts = [
        tapered_box(
            "TorsoShell",
            (0.0, 0.0, 1.235),
            0.43,
            TORSO_WIDTH * 0.78,
            TORSO_WIDTH,
            TORSO_DEPTH * 0.92,
            TORSO_DEPTH,
            suit,
            bevel=0.016,
        ),
        cube_part(
            "ShoulderYoke",
            (0.0, 0.035, 1.410),
            (0.555, 0.225, 0.105),
            MATERIALS["M_Helmet"],
            bevel=0.014,
        ),
        cube_part(
            "ChestPanel",
            (0.0, -0.153, 1.285),
            (0.355, 0.035, 0.205),
            dark,
            bevel=0.012,
        ),
        cube_part(
            "WarningSlash",
            (-0.030, -0.176, 1.295),
            (0.300, 0.022, 0.045),
            warning,
            bevel=0.004,
            rotation=(0.0, math.radians(-12.0), 0.0),
        ),
        cube_part(
            "ChestVent",
            (-0.125, -0.177, 1.225),
            (0.090, 0.020, 0.025),
            metal,
            bevel=0.003,
        ),
        cube_part(
            "ChestVent",
            (0.0, -0.177, 1.225),
            (0.090, 0.020, 0.025),
            metal,
            bevel=0.003,
        ),
        cylinder_part(
            "CompanyBadge",
            (0.155, -0.180, 1.355),
            0.040,
            0.020,
            warning,
            vertices=6,
            rotation=(math.radians(90), 0.0, 0.0),
            bevel=0.002,
        ),
    ]
    return join_parts(parts, "SM_Torso", "Body", origin_point=(0.0, 0.0, 1.035))


def create_pelvis():
    suit = MATERIALS["M_Suit"]
    dark = MATERIALS["M_Dark"]
    warning = MATERIALS["M_Warning"]
    parts = [
        tapered_box(
            "PelvisShell",
            (0.0, 0.0, 1.005),
            0.205,
            0.42,
            0.45,
            0.255,
            0.27,
            suit,
            bevel=0.014,
        ),
        cube_part(
            "UtilityBelt",
            (0.0, -0.005, 1.075),
            (0.475, 0.285, 0.072),
            dark,
            bevel=0.008,
        ),
        cube_part(
            "BeltBuckle",
            (0.0, -0.158, 1.075),
            (0.095, 0.025, 0.070),
            warning,
            bevel=0.006,
        ),
        cube_part(
            "HipPouch",
            (-0.215, 0.005, 0.985),
            (0.090, 0.185, 0.150),
            dark,
            bevel=0.010,
        ),
    ]
    return join_parts(parts, "SM_Pelvis", "Body", origin_point=(0.0, 0.0, 1.02))


def create_arm(side):
    sign = -1.0 if side == "L" else 1.0
    suffix = side
    suit = MATERIALS["M_Suit"]
    dark = MATERIALS["M_Dark"]
    helmet = MATERIALS["M_Helmet"]

    shoulder = Vector((sign * 0.310, 0.0, 1.395))
    elbow = Vector((sign * (0.515 * ARM_LENGTH_SCALE), -0.005, 1.135))
    wrist = Vector((sign * (0.665 * ARM_LENGTH_SCALE), -0.012, 0.910))
    hand_end = Vector((sign * (0.735 * ARM_LENGTH_SCALE), -0.020, 0.745))

    upper_parts = [
        lowpoly_sphere(
            "ShoulderCap",
            shoulder,
            0.128,
            helmet,
            subdivisions=2,
            scale=(0.95, 1.0, 1.0),
        ),
        cone_between(
            "UpperSleeve",
            shoulder,
            elbow,
            0.108,
            0.092,
            suit,
            bevel=0.006,
        ),
        cylinder_part(
            "UpperSleeveBand",
            shoulder.lerp(elbow, 0.72),
            0.102,
            0.045,
            dark,
            rotation=direction_rotation(shoulder, elbow),
            bevel=0.004,
        ),
    ]
    upper = join_parts(
        upper_parts,
        f"SM_UpperArm_{suffix}",
        "Body",
        origin_point=shoulder,
    )

    lower_parts = [
        cone_between(
            "LowerSleeve",
            elbow,
            wrist,
            0.096,
            0.078,
            suit,
            bevel=0.006,
        ),
        lowpoly_sphere(
            "ElbowPad",
            elbow,
            0.101,
            dark,
            subdivisions=2,
            scale=(0.92, 1.0, 1.0),
        ),
        cylinder_part(
            "GloveCuff",
            wrist,
            0.098,
            0.075,
            dark,
            rotation=direction_rotation(elbow, wrist),
            bevel=0.005,
        ),
    ]
    lower = join_parts(
        lower_parts,
        f"SM_LowerArm_{suffix}",
        "Body",
        origin_point=elbow,
    )

    hand_mid = wrist.lerp(hand_end, 0.53)
    hand_rotation = direction_rotation(wrist, hand_end)
    hand_parts = [
        cube_part(
            "Mitten",
            hand_mid,
            (0.145 * HAND_SCALE, 0.135 * HAND_SCALE, 0.180 * HAND_SCALE),
            dark,
            bevel=0.035,
            rotation=hand_rotation,
        ),
        lowpoly_sphere(
            "MittenKnuckle",
            hand_end,
            0.080 * HAND_SCALE,
            dark,
            subdivisions=2,
            scale=(0.88, 0.95, 1.0),
        ),
        lowpoly_sphere(
            "MittenThumb",
            hand_mid + Vector((-sign * 0.045, -0.052, 0.005)),
            0.043 * HAND_SCALE,
            dark,
            subdivisions=1,
            scale=(0.9, 1.15, 1.0),
        ),
    ]
    hand = join_parts(
        hand_parts,
        f"SM_Hand_{suffix}",
        "Body",
        origin_point=wrist,
    )
    return upper, lower, hand


def create_leg(side):
    sign = -1.0 if side == "L" else 1.0
    suffix = side
    suit = MATERIALS["M_Suit"]
    dark = MATERIALS["M_Dark"]
    helmet = MATERIALS["M_Helmet"]
    metal = MATERIALS["M_Metal"]

    hip = Vector((sign * 0.135, 0.0, 0.970))
    knee = Vector((sign * 0.145, -0.004, 0.620))
    ankle = Vector((sign * 0.150, 0.010, 0.245))

    upper_parts = [
        cone_between(
            "UpperLegSuit",
            hip,
            knee,
            LEG_THICKNESS * 0.90,
            LEG_THICKNESS * 0.76,
            suit,
            bevel=0.007,
        ),
        cylinder_part(
            "HipSeal",
            hip.lerp(knee, 0.12),
            LEG_THICKNESS * 0.93,
            0.045,
            dark,
            rotation=direction_rotation(hip, knee),
            bevel=0.004,
        ),
    ]
    upper = join_parts(
        upper_parts,
        f"SM_UpperLeg_{suffix}",
        "Body",
        origin_point=hip,
    )

    lower_parts = [
        cone_between(
            "LowerLegSuit",
            knee,
            ankle,
            LEG_THICKNESS * 0.78,
            LEG_THICKNESS * 0.68,
            suit,
            bevel=0.007,
        ),
        lowpoly_sphere(
            "KneePad",
            knee + Vector((0.0, -0.055, 0.0)),
            LEG_THICKNESS * 0.78,
            helmet,
            subdivisions=2,
            scale=(0.95, 0.55, 0.90),
        ),
        cylinder_part(
            "BootCuff",
            ankle,
            LEG_THICKNESS * 0.80,
            0.085,
            dark,
            rotation=direction_rotation(knee, ankle),
            bevel=0.005,
        ),
    ]
    lower = join_parts(
        lower_parts,
        f"SM_LowerLeg_{suffix}",
        "Body",
        origin_point=knee,
    )

    boot_x = sign * 0.150
    boot_parts = [
        tapered_box(
            "BootBody",
            (boot_x, -0.035, 0.115),
            0.230,
            0.220 * BOOT_SCALE,
            0.205 * BOOT_SCALE,
            0.370 * BOOT_SCALE,
            0.315 * BOOT_SCALE,
            dark,
            bevel=0.018,
        ),
        cube_part(
            "BootToeCap",
            (boot_x, -0.205, 0.090),
            (0.225 * BOOT_SCALE, 0.150 * BOOT_SCALE, 0.120),
            helmet,
            bevel=0.022,
        ),
        cube_part(
            "BootSole",
            (boot_x, -0.050, 0.026),
            (0.235 * BOOT_SCALE, 0.395 * BOOT_SCALE, 0.052),
            helmet,
            bevel=0.010,
        ),
        cube_part(
            "BootBuckle",
            (boot_x, -0.213, 0.145),
            (0.100, 0.022, 0.050),
            metal,
            bevel=0.004,
        ),
    ]
    foot = join_parts(
        boot_parts,
        f"SM_Foot_{suffix}",
        "Body",
        origin_point=ankle,
    )
    return upper, lower, foot


def create_backpack():
    dark = MATERIALS["M_Dark"]
    metal = MATERIALS["M_Metal"]
    helmet = MATERIALS["M_Helmet"]
    warning = MATERIALS["M_Warning"]
    parts = [
        cube_part(
            "PackFrame",
            (0.0, 0.202, 1.235),
            (0.335, 0.165, 0.390),
            helmet,
            collection="Equipment",
            bevel=0.018,
        ),
        cube_part(
            "PackInset",
            (0.0, 0.295, 1.235),
            (0.245, 0.055, 0.285),
            dark,
            collection="Equipment",
            bevel=0.014,
        ),
        cylinder_part(
            "PackTank",
            (-0.118, 0.325, 1.245),
            0.066,
            0.305,
            metal,
            collection="Equipment",
            vertices=8,
            bevel=0.006,
        ),
        cylinder_part(
            "TankCap",
            (-0.118, 0.325, 1.415),
            0.050,
            0.045,
            warning,
            collection="Equipment",
            vertices=8,
            bevel=0.004,
        ),
        cube_part(
            "PackStatus",
            (0.085, 0.331, 1.325),
            (0.085, 0.020, 0.075),
            warning,
            collection="Equipment",
            bevel=0.006,
        ),
        cube_part(
            "PackLowerGuard",
            (0.075, 0.325, 1.090),
            (0.120, 0.030, 0.060),
            metal,
            collection="Equipment",
            bevel=0.005,
        ),
    ]

    cable_points = [
        (0.135, 0.335, 1.375),
        (0.205, 0.330, 1.335),
        (0.205, 0.290, 1.145),
        (0.145, 0.270, 1.085),
    ]
    for index, (start, end) in enumerate(zip(cable_points, cable_points[1:])):
        parts.append(
            cone_between(
                f"PackCable_{index}",
                start,
                end,
                0.014,
                0.014,
                dark,
                collection="Equipment",
                vertices=6,
                bevel=0.002,
            )
        )
    return join_parts(
        parts,
        "SM_Backpack",
        "Equipment",
        origin_point=(0.0, 0.135, 1.385),
    )


def create_character():
    create_head()
    create_neck()
    create_torso()
    create_pelvis()
    create_arm("L")
    create_arm("R")
    create_leg("L")
    create_leg("R")
    create_backpack()


def scale_character_to_height():
    """Scale geometry and joint origins together when CHARACTER_HEIGHT changes."""
    scale_factor = CHARACTER_HEIGHT / BASE_CHARACTER_HEIGHT
    if abs(scale_factor - 1.0) <= 1e-8:
        return
    for obj in export_meshes():
        obj.location *= scale_factor
        obj.scale = (scale_factor, scale_factor, scale_factor)
        apply_transforms(obj)


# -----------------------------------------------------------------------------
# Preview, validation, and output

def point_object_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def create_area_light(name, location, energy, color, size):
    data = bpy.data.lights.new(name, type="AREA")
    data.energy = energy
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    COLLECTIONS["Preview"].objects.link(obj)
    obj.location = location
    point_object_at(
        obj,
        (0.0, 0.0, 0.95 * CHARACTER_HEIGHT / BASE_CHARACTER_HEIGHT),
    )
    return obj


def setup_preview():
    scene = bpy.context.scene
    preview_scale = CHARACTER_HEIGHT / BASE_CHARACTER_HEIGHT
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.008, 0.013, 0.015, 1.0)
    background.inputs["Strength"].default_value = 0.16

    ground = cylinder_part(
        "SM_PreviewGround",
        (0.0, 0.0, -0.035 * preview_scale),
        1.20 * preview_scale,
        0.070 * preview_scale,
        MATERIALS["M_Dark"],
        collection="Preview",
        vertices=12,
        bevel=0.015,
    )
    ground["ue_export"] = False

    create_area_light(
        "LGT_Key",
        (-2.7 * preview_scale, -3.2 * preview_scale, 3.6 * preview_scale),
        850.0,
        (1.0, 0.70, 0.43),
        2.2,
    )
    create_area_light(
        "LGT_Fill",
        (2.8 * preview_scale, -2.1 * preview_scale, 2.0 * preview_scale),
        520.0,
        (0.32, 0.62, 0.72),
        2.5,
    )
    create_area_light(
        "LGT_Rim",
        (0.7 * preview_scale, 2.6 * preview_scale, 2.9 * preview_scale),
        920.0,
        (0.23, 0.68, 0.62),
        1.8,
    )

    camera_data = bpy.data.cameras.new("CAM_CharacterPreview")
    camera = bpy.data.objects.new("CAM_CharacterPreview", camera_data)
    COLLECTIONS["Preview"].objects.link(camera)
    camera.location = (
        2.75 * preview_scale,
        -4.75 * preview_scale,
        2.18 * preview_scale,
    )
    camera_data.lens = 62.0
    camera_data.sensor_width = 36.0
    point_object_at(camera, (0.0, 0.0, 0.93 * preview_scale))
    scene.camera = camera

    scene.render.resolution_x = 720
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = PREVIEW_PATH.as_posix()
    scene.render.film_transparent = False

    available_looks = {
        item.identifier
        for item in scene.view_settings.bl_rna.properties["look"].enum_items
    }
    preferred = "AgX - Medium High Contrast"
    scene.view_settings.look = preferred if preferred in available_looks else "None"


def export_meshes():
    return [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.get("ue_export", False)
    ]


def scene_statistics():
    all_objects = list(bpy.context.scene.objects)
    meshes = export_meshes()
    triangles = 0
    for obj in meshes:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
    minimum, maximum = world_bounds(meshes)
    return {
        "objects": len(all_objects),
        "meshes": len(meshes),
        "materials": len(bpy.data.materials),
        "triangles": triangles,
        "armature": any(obj.type == "ARMATURE" for obj in all_objects),
        "height": maximum.z - minimum.z,
        "minimum": minimum,
        "maximum": maximum,
    }


def validate_scene():
    required_objects = {
        "SM_Head",
        "SM_Neck",
        "SM_Torso",
        "SM_Pelvis",
        "SM_UpperArm_L",
        "SM_LowerArm_L",
        "SM_Hand_L",
        "SM_UpperArm_R",
        "SM_LowerArm_R",
        "SM_Hand_R",
        "SM_UpperLeg_L",
        "SM_LowerLeg_L",
        "SM_Foot_L",
        "SM_UpperLeg_R",
        "SM_LowerLeg_R",
        "SM_Foot_R",
        "SM_Backpack",
    }
    missing = sorted(required_objects - set(bpy.data.objects.keys()))
    if missing:
        raise RuntimeError(f"Missing required character objects: {missing}")

    required_collections = {"LowPolyWorker", "Body", "Equipment", "Rig", "Preview"}
    missing_collections = sorted(required_collections - set(bpy.data.collections.keys()))
    if missing_collections:
        raise RuntimeError(f"Missing collections: {missing_collections}")

    invalid_transforms = []
    mesh_name_mismatches = []
    for obj in export_meshes():
        if obj.data.name != obj.name:
            mesh_name_mismatches.append(f"{obj.name} -> {obj.data.name}")
        if any(abs(value - 1.0) > 1e-5 for value in obj.scale):
            invalid_transforms.append(f"{obj.name}: scale")
        if any(abs(value) > 1e-5 for value in obj.rotation_euler):
            invalid_transforms.append(f"{obj.name}: rotation")
    if invalid_transforms:
        raise RuntimeError(f"Unapplied character transforms: {invalid_transforms}")
    if mesh_name_mismatches:
        raise RuntimeError(f"Mesh datablock name mismatch: {mesh_name_mismatches}")

    stats = scene_statistics()
    if stats["materials"] > 6:
        raise RuntimeError(f"Material count must be <= 6, got {stats['materials']}")
    if stats["triangles"] > 15_000:
        raise RuntimeError(f"Triangle count must be < 15,000, got {stats['triangles']}")
    if abs(stats["height"] - CHARACTER_HEIGHT) > 0.02:
        raise RuntimeError(
            f"Character height must be about {CHARACTER_HEIGHT:.2f} m, "
            f"got {stats['height']:.4f}"
        )
    if abs(stats["minimum"].z) > 0.012:
        raise RuntimeError(f"Feet must sit at Z=0, minimum is {stats['minimum'].z:.4f}")
    if abs((stats["minimum"].x + stats["maximum"].x) * 0.5) > 0.015:
        raise RuntimeError("Character is not centered around world X=0")
    return stats


def save_and_export():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.filepath = PREVIEW_PATH.as_posix()
    bpy.ops.render.render(write_still=True)

    camera = scene.camera
    front_location = camera.location.copy()
    front_rotation = camera.rotation_euler.copy()
    preview_scale = CHARACTER_HEIGHT / BASE_CHARACTER_HEIGHT
    camera.location = (
        -2.75 * preview_scale,
        4.75 * preview_scale,
        2.18 * preview_scale,
    )
    point_object_at(camera, (0.0, 0.0, 0.93 * preview_scale))
    scene.render.filepath = BACK_PREVIEW_PATH.as_posix()
    bpy.ops.render.render(write_still=True)
    camera.location = front_location
    camera.rotation_euler = front_rotation
    scene.render.filepath = PREVIEW_PATH.as_posix()

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH.as_posix(), check_existing=False)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in export_meshes():
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
    setup_units()
    create_collections()
    create_materials()
    create_character()
    scale_character_to_height()
    setup_preview()

    stats = validate_scene()
    save_and_export()

    print("\n=== Low Poly Worker Generation Complete ===\n")
    print(f"Objects:          {stats['objects']}")
    print(f"Meshes:           {stats['meshes']}")
    print(f"Materials:        {stats['materials']}")
    print(f"Triangles:        {stats['triangles']}")
    print(f"Armature:         {'Yes' if stats['armature'] else 'No (segmented rig-ready mesh)'}")
    print(f"Character Height: {stats['height']:.3f} m")
    print(f"Blend:            {BLEND_PATH}")
    print(f"FBX:              {FBX_PATH}")
    print(f"Preview:          {PREVIEW_PATH}\n")
    print(f"Back Preview:     {BACK_PREVIEW_PATH}\n")


if __name__ == "__main__":
    main()
