import unreal


MAP_PATH = "/Game/Prototype/Maps/L_Prototype"
CHARACTER_PATH = "/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter"
WALK_SPEED = 350.0

asset_subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(message):
    unreal.log(f"[T00PlaytestFix] {message}")


def update_walk_speed():
    blueprint = asset_subsystem.load_asset(CHARACTER_PATH)
    character_class = asset_subsystem.load_blueprint_class(CHARACTER_PATH)
    if blueprint is None or character_class is None:
        raise RuntimeError("Could not load BP_FirstPersonCharacter")
    character_cdo = unreal.get_default_object(character_class)
    movement = character_cdo.get_component_by_class(unreal.CharacterMovementComponent)
    if movement is None:
        raise RuntimeError("BP_FirstPersonCharacter has no CharacterMovementComponent")
    movement.set_editor_property("max_walk_speed", WALK_SPEED)
    blueprint.modify()
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    asset_subsystem.save_loaded_asset(blueprint, only_if_is_dirty=False)
    log(f"Max Walk Speed set to {WALK_SPEED} cm/s and Blueprint compiled")


def update_level():
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Could not load L_Prototype")

    lights_changed = 0
    post_process = None
    nav_bounds = None
    for actor in actor_subsystem.get_all_level_actors():
        label = actor.get_actor_label()
        if label.startswith("LIGHT_ColdMain_"):
            component = actor.get_component_by_class(unreal.LightComponent)
            component.set_mobility(unreal.ComponentMobility.MOVABLE)
            component.set_editor_property("intensity", 1200.0)
            lights_changed += 1
        elif label == "LIGHT_RedWarning":
            component = actor.get_component_by_class(unreal.LightComponent)
            component.set_mobility(unreal.ComponentMobility.MOVABLE)
            component.set_editor_property("intensity", 350.0)
            lights_changed += 1
        elif label == "PROTOTYPE_PostProcess":
            post_process = actor
        elif label == "PROTOTYPE_NavMeshBounds":
            nav_bounds = actor

    if nav_bounds is not None:
        nav_bounds.set_actor_location(unreal.Vector(0.0, 0.0, 100.0), False, False)
        nav_bounds.set_actor_scale3d(unreal.Vector(8.0, 10.0, 3.0))

    if post_process is None:
        post_process = actor_subsystem.spawn_actor_from_class(
            unreal.PostProcessVolume,
            unreal.Vector(0.0, 0.0, 0.0),
            unreal.Rotator(0.0, 0.0, 0.0),
            transient=False,
        )
        post_process.set_actor_label("PROTOTYPE_PostProcess")
    post_process.set_editor_property("unbound", True)
    settings = post_process.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", -1.0)
    settings.set_editor_property("override_bloom_intensity", True)
    settings.set_editor_property("bloom_intensity", 0.25)
    post_process.set_editor_property("settings", settings)

    if nav_bounds is None:
        raise RuntimeError("PROTOTYPE_NavMeshBounds is missing")
    world = unreal.EditorLevelLibrary.get_editor_world()
    nav_system = unreal.NavigationSystemV1.get_navigation_system(world)
    if nav_system is None:
        raise RuntimeError("NavigationSystemV1 is unavailable")
    nav_system.on_navigation_bounds_updated(nav_bounds)
    unreal.SystemLibrary.execute_console_command(world, "RebuildNavigation")

    if not level_subsystem.save_current_level():
        raise RuntimeError("Could not save L_Prototype")
    log(f"Updated {lights_changed} lights to Movable, reduced exposure, rebuilt navigation, and saved level")


update_walk_speed()
update_level()
log("Playtest fixes complete")
