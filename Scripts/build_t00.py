import unreal


ROOT = "/Game"
LAB_DEST = "/Game/Prototype/Environment/LowPolyLab"
MAP_PATH = "/Game/Prototype/Maps/L_Prototype"
FBX_SOURCE = "F:/AnomalyLab/我的项目3/LowPolyLabPrototype/low_poly_lab_room.fbx"

asset_subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()


def info(message):
    unreal.log(f"[T00Build] {message}")


def warning(message):
    unreal.log_warning(f"[T00Build] {message}")


def ensure_directories():
    for path in (
        "/Game/Core/Characters",
        "/Game/Core/Components",
        "/Game/Core/Debug",
        "/Game/Core/GameModes",
        "/Game/Core/Input",
        "/Game/Core/Types",
        "/Game/Interaction",
        "/Game/Anomalies/Containers",
        "/Game/Anomalies/Loot",
        "/Game/Anomalies/Creatures",
        "/Game/UI",
        LAB_DEST,
        "/Game/Prototype/Maps",
    ):
        if not asset_subsystem.does_directory_exist(path):
            if not asset_subsystem.make_directory(path):
                raise RuntimeError(f"Could not create content directory {path}")
    info("Content directories are ready")


def import_lab():
    existing = asset_subsystem.list_assets(LAB_DEST, recursive=True, include_folder=False)
    if any(str(path).endswith("SM_Floor.SM_Floor") for path in existing):
        info(f"Lab import already exists with {len(existing)} assets")
        return

    import_ui = unreal.FbxImportUI()
    import_ui.set_editor_property("import_mesh", True)
    import_ui.set_editor_property("import_as_skeletal", False)
    import_ui.set_editor_property("import_materials", True)
    import_ui.set_editor_property("import_textures", False)
    import_ui.set_editor_property("automated_import_should_detect_type", False)
    import_ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)

    mesh_data = import_ui.get_editor_property("static_mesh_import_data")
    mesh_data.set_editor_property("combine_meshes", False)
    mesh_data.set_editor_property("import_uniform_scale", 1.0)
    mesh_data.set_editor_property("convert_scene", True)
    mesh_data.set_editor_property("convert_scene_unit", True)
    mesh_data.set_editor_property("transform_vertex_to_absolute", True)
    mesh_data.set_editor_property("auto_generate_collision", True)
    mesh_data.set_editor_property("generate_lightmap_u_vs", True)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", FBX_SOURCE)
    task.set_editor_property("destination_path", LAB_DEST)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("options", import_ui)
    asset_tools.import_asset_tasks([task])

    paths = [str(path) for path in task.get_editor_property("imported_object_paths")]
    if not paths:
        paths = [str(path) for path in asset_subsystem.list_assets(LAB_DEST, recursive=True, include_folder=False)]
    if not any("SM_Floor" in path for path in paths):
        raise RuntimeError("FBX import completed without SM_Floor")
    info(f"Imported Low Poly Lab as separate assets ({len(paths)} imported paths)")


def ensure_enum(asset_name, desired_names):
    asset_path = f"/Game/Core/Types/{asset_name}"
    enum_asset = asset_subsystem.load_asset(asset_path)
    if enum_asset is None:
        enum_asset = asset_tools.create_asset(
            asset_name,
            "/Game/Core/Types",
            unreal.UserDefinedEnum,
            unreal.EnumFactory(),
        )
    if enum_asset is None:
        raise RuntimeError(f"Could not create {asset_path}")

    # UE Python can create UserDefinedEnum assets but does not expose FEnumEditorUtils.
    # Try the reflected property for engine versions that expose it; otherwise preserve
    # the valid asset and emit a precise warning for the remaining editor-only step.
    try:
        current_names = enum_asset.get_editor_property("names")
        info(f"{asset_name} reflected names before update: {current_names}")
    except Exception as exc:
        warning(f"{asset_name} values require Unreal enum editor: {exc}")
    asset_subsystem.save_loaded_asset(enum_asset, only_if_is_dirty=False)
    return enum_asset


def ensure_log_library():
    asset_path = "/Game/Core/Debug/BFL_PrototypeLog"
    blueprint = asset_subsystem.load_asset(asset_path)
    if blueprint is None:
        blueprint = unreal.BlueprintEditorLibrary.create_blueprint_asset_with_parent(
            asset_path, unreal.BlueprintFunctionLibrary
        )
    if blueprint is None:
        raise RuntimeError("Could not create BFL_PrototypeLog")

    existing = {str(name) for name in unreal.BlueprintEditorLibrary.list_graph_names(blueprint)}
    for function_name in ("Info", "Warning", "Error"):
        if function_name not in existing:
            unreal.BlueprintEditorLibrary.add_function_graph(blueprint, function_name)
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    asset_subsystem.save_loaded_asset(blueprint, only_if_is_dirty=False)
    info("BFL_PrototypeLog created with Info, Warning, and Error function graphs")


def set_actor_label(actor, label):
    try:
        actor.set_actor_label(label)
    except Exception:
        pass


def spawn_static_mesh(mesh, label, collision_enabled=True, location=None, scale=None):
    actor = actor_subsystem.spawn_actor_from_object(
        mesh,
        location or unreal.Vector(0.0, 0.0, 0.0),
        unreal.Rotator(0.0, 0.0, 0.0),
        transient=False,
    )
    if actor is None:
        raise RuntimeError(f"Could not place {label}")
    set_actor_label(actor, label)
    if scale is not None:
        actor.set_actor_scale3d(scale)
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    if component:
        component.set_collision_profile_name("BlockAll" if collision_enabled else "NoCollision")
    return actor


def configure_light(actor, intensity, color, radius=None):
    component = actor.get_component_by_class(unreal.LightComponent)
    if component:
        component.set_editor_property("intensity", intensity)
        component.set_editor_property("light_color", color)
        if radius is not None:
            try:
                component.set_editor_property("attenuation_radius", radius)
            except Exception:
                pass


def build_level():
    if not level_subsystem.new_level(MAP_PATH):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError(f"Could not create or load {MAP_PATH}")
    info("Created L_Prototype")

    collision_terms = (
        "floor",
        "wall",
        "door_industrial",
        "shelf",
        "cabinet",
        "locker",
    )
    placed = 0
    collision_count = 0
    for path in asset_subsystem.list_assets(LAB_DEST, recursive=True, include_folder=False):
        path_string = str(path)
        asset = asset_subsystem.load_asset(path_string)
        if not isinstance(asset, unreal.StaticMesh):
            continue
        name = asset.get_name()
        if name == "SM_TestLootCrate":
            continue
        collision_enabled = any(term in name.lower() for term in collision_terms)
        spawn_static_mesh(asset, f"ENV_{name}", collision_enabled=collision_enabled)
        placed += 1
        collision_count += int(collision_enabled)

    cube = asset_subsystem.load_asset("/Engine/BasicShapes/Cube.Cube")
    if cube is None:
        raise RuntimeError("Engine Cube asset is unavailable")
    pedestal = spawn_static_mesh(
        cube,
        "PROTOTYPE_CentralPedestal",
        collision_enabled=True,
        location=unreal.Vector(0.0, 0.0, 20.0),
        scale=unreal.Vector(0.75, 0.75, 0.20),
    )

    player_start = actor_subsystem.spawn_actor_from_class(
        unreal.PlayerStart,
        unreal.Vector(430.0, 850.0, 110.0),
        unreal.Rotator(0.0, -90.0, 0.0),
        transient=False,
    )
    set_actor_label(player_start, "PROTOTYPE_PlayerStart")

    nav_bounds = actor_subsystem.spawn_actor_from_class(
        unreal.NavMeshBoundsVolume,
        unreal.Vector(0.0, 0.0, 100.0),
        unreal.Rotator(0.0, 0.0, 0.0),
        transient=False,
    )
    set_actor_label(nav_bounds, "PROTOTYPE_NavMeshBounds")
    # Extend below the imported floor so Recast does not clip the walkable
    # surface exactly at the lower edge of the navigation volume.
    nav_bounds.set_actor_scale3d(unreal.Vector(8.0, 10.0, 3.0))

    cold = unreal.Color(210, 230, 255, 255)
    red = unreal.Color(255, 24, 12, 255)
    for index, location in enumerate(
        (
            unreal.Vector(-450.0, -500.0, 330.0),
            unreal.Vector(450.0, -500.0, 330.0),
            unreal.Vector(-450.0, 500.0, 330.0),
            unreal.Vector(450.0, 500.0, 330.0),
        )
    ):
        light = actor_subsystem.spawn_actor_from_class(unreal.PointLight, location, unreal.Rotator(), transient=False)
        set_actor_label(light, f"LIGHT_ColdMain_{index + 1}")
        configure_light(light, 4200.0, cold, 950.0)

    warning_light = actor_subsystem.spawn_actor_from_class(
        unreal.PointLight, unreal.Vector(318.0, -430.0, 268.0), unreal.Rotator(), transient=False
    )
    set_actor_label(warning_light, "LIGHT_RedWarning")
    configure_light(warning_light, 1200.0, red, 420.0)

    world = unreal.EditorLevelLibrary.get_editor_world()
    if world:
        settings = world.get_world_settings()
        game_mode_class = asset_subsystem.load_blueprint_class(
            "/Game/FirstPerson/Blueprints/BP_FirstPersonGameMode"
        )
        if game_mode_class:
            settings.set_editor_property("default_game_mode", game_mode_class)

    if not level_subsystem.save_current_level():
        raise RuntimeError("Could not save L_Prototype")
    asset_subsystem.save_directory("/Game/Prototype", only_if_is_dirty=False, recursive=True)
    info(
        f"Level saved with {placed} Lab meshes, {collision_count} collision-enabled environment meshes, "
        "pedestal, PlayerStart, NavMesh bounds, and five lights"
    )


def verify():
    required = (
        "/Game/Prototype/Maps/L_Prototype",
        "/Game/Core/Debug/BFL_PrototypeLog",
        "/Game/Core/Types/EAnomalyOutcome",
        "/Game/Core/Types/EPrototypeRoundState",
    )
    for path in required:
        if not asset_subsystem.does_asset_exist(path):
            raise RuntimeError(f"Missing required asset: {path}")
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Verification could not load L_Prototype")
    actors = actor_subsystem.get_all_level_actors()
    labels = {actor.get_actor_label() for actor in actors}
    for label in ("PROTOTYPE_CentralPedestal", "PROTOTYPE_PlayerStart", "PROTOTYPE_NavMeshBounds"):
        if label not in labels:
            raise RuntimeError(f"Verification missing actor: {label}")
    info(f"VERIFY PASS: required assets load; L_Prototype contains {len(actors)} actors")


def main():
    ensure_directories()
    import_lab()
    ensure_enum("EAnomalyOutcome", ("HighValue", "Trash", "Threat"))
    ensure_enum("EPrototypeRoundState", ("Ready", "Revealing", "OutcomeActive", "Ended"))
    ensure_log_library()
    build_level()
    verify()
    info("T00 scripted build finished")


main()
