import unreal


asset_subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(message):
    unreal.log(f"[T00Validate] {message}")


if not level_subsystem.load_level("/Game/Prototype/Maps/L_Prototype"):
    raise RuntimeError("Could not load L_Prototype")

actors = actor_subsystem.get_all_level_actors()
by_label = {actor.get_actor_label(): actor for actor in actors}

for label in (
    "ENV_SM_Floor",
    "ENV_SM_Wall_A",
    "ENV_SM_Wall_B",
    "ENV_SM_Wall_Back",
    "ENV_SM_Wall_Front",
    "ENV_SM_Door_Industrial",
    "PROTOTYPE_CentralPedestal",
    "PROTOTYPE_PlayerStart",
    "PROTOTYPE_NavMeshBounds",
):
    actor = by_label.get(label)
    if actor is None:
        raise RuntimeError(f"Missing required actor {label}")
    origin, extent = actor.get_actor_bounds(False)
    log(f"{label}: origin={origin}, extent={extent}, location={actor.get_actor_location()}")

for label in ("ENV_SM_Floor", "ENV_SM_Door_Industrial", "PROTOTYPE_CentralPedestal"):
    component = by_label[label].get_component_by_class(unreal.StaticMeshComponent)
    if not component or component.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION:
        raise RuntimeError(f"Required collision is disabled on {label}")

for label in ("ENV_SM_Drain", "ENV_SM_RetroComputer", "ENV_SM_ScrapMetal_A"):
    component = by_label[label].get_component_by_class(unreal.StaticMeshComponent)
    if component and component.get_collision_enabled() != unreal.CollisionEnabled.NO_COLLISION:
        raise RuntimeError(f"Decorative collision should be disabled on {label}")

blueprint = asset_subsystem.load_asset("/Game/Core/Debug/BFL_PrototypeLog")
for function_name, expected_screen in (("Info", "False"), ("Warning", "True"), ("Error", "True")):
    editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(blueprint, function_name)
    errors = editor.list_nodes_with_errors()
    call_nodes = [node for node in editor.list_all_nodes() if isinstance(node, unreal.K2Node_CallFunction)]
    if errors or len(call_nodes) != 1:
        raise RuntimeError(f"{function_name} graph validation failed: errors={errors}, calls={len(call_nodes)}")
    call_node = call_nodes[0]
    screen_value = unreal.BlueprintGraphPinLibrary.get_pin_value(call_node.find_input_pin("bPrintToScreen"))
    log(f"{function_name}: PrintToScreen={screen_value}, node_errors={len(errors)}")

for enum_path in ("/Game/Core/Types/EAnomalyOutcome", "/Game/Core/Types/EPrototypeRoundState"):
    asset = asset_subsystem.load_asset(enum_path)
    if asset is None:
        raise RuntimeError(f"Missing {enum_path}")
    log(f"Enum asset loads: {enum_path}")

world = unreal.EditorLevelLibrary.get_editor_world()
game_mode = world.get_world_settings().get_editor_property("default_game_mode")
log(f"World default game mode: {game_mode}")
log(f"VALIDATION PASS: {len(actors)} actors; environment, collision, log graphs, and base assets load")

