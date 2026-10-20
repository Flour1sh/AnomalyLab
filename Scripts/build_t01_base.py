import unreal


PREFIX = "[T01Base]"
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()

BPI_PATH = "/Game/Interaction/BPI_Interactable"
COMPONENT_PATH = "/Game/Core/Components/BPC_Interaction"
ACTION_PATH = "/Game/Core/Input/IA_Interact"
CONTEXT_PATH = "/Game/Core/Input/IMC_Prototype"
BOX_PATH = "/Game/Anomalies/Containers/BP_AnomalyBox"
CHARACTER_PATH = "/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter"
MAP_PATH = "/Game/Prototype/Maps/L_Prototype"


def log(message):
    unreal.log(f"{PREFIX} {message}")


def require_asset(path):
    asset = ASSETS.load_asset(path)
    if asset is None:
        raise RuntimeError(f"Missing required asset {path}")
    return asset


def ensure_blueprint(path, parent_class):
    blueprint = ASSETS.load_asset(path)
    if blueprint is None:
        blueprint = unreal.BlueprintEditorLibrary.create_blueprint_asset_with_parent(path, parent_class)
    if blueprint is None:
        raise RuntimeError(f"Could not create {path}")
    return blueprint


def ensure_interface_signature():
    blueprint = require_asset(BPI_PATH)
    graphs = {str(name): name for name in unreal.BlueprintEditorLibrary.list_graph_names(blueprint)}
    if "Interact" not in graphs:
        graph = unreal.BlueprintEditorLibrary.add_function_graph(blueprint, "Interact")
    else:
        graph = unreal.BlueprintEditorLibrary.find_graph(blueprint, unreal.Name("Interact"))
    if graph is None:
        raise RuntimeError("Could not create BPI_Interactable.Interact")
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    entry = next(
        node for node in editor.list_all_nodes() if isinstance(node, unreal.K2Node_FunctionEntry)
    )
    output_names = {
        str(unreal.BlueprintGraphPinLibrary.get_pin_name(pin))
        for pin in unreal.BlueprintEditorLibrary.list_output_pins(entry)
    }
    if "Interactor" not in output_names:
        actor_type = unreal.BlueprintEditorLibrary.get_object_reference_type(unreal.Actor.static_class())
        if not editor.add_graph_input_parameter("Interactor", actor_type, ""):
            raise RuntimeError("Could not add Interactor Actor parameter to interface")
    editor.set_function_is_public()
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    ASSETS.save_loaded_asset(blueprint, only_if_is_dirty=False)
    log("BPI_Interactable.Interact(Interactor: Actor) ready")


def ensure_input_assets():
    action = ASSETS.load_asset(ACTION_PATH)
    if action is None:
        factory_class = getattr(unreal, "InputAction_Factory", None)
        factory = factory_class() if factory_class else None
        action = ASSET_TOOLS.create_asset("IA_Interact", "/Game/Core/Input", unreal.InputAction, factory)
    if action is None:
        raise RuntimeError("Could not create IA_Interact")
    action.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)

    context = ASSETS.load_asset(CONTEXT_PATH)
    if context is None:
        factory_class = getattr(unreal, "InputMappingContext_Factory", None)
        factory = factory_class() if factory_class else None
        context = ASSET_TOOLS.create_asset(
            "IMC_Prototype", "/Game/Core/Input", unreal.InputMappingContext, factory
        )
    if context is None:
        raise RuntimeError("Could not create IMC_Prototype")

    mapping = unreal.EnhancedActionKeyMapping()
    mapping.set_editor_property("action", action)
    key = unreal.Key()
    key.set_editor_property("key_name", unreal.Name("E"))
    mapping.set_editor_property("key", key)
    mapping_data = unreal.InputMappingContextMappingData()
    mapping_data.set_editor_property("mappings", [mapping])
    context.set_editor_property("default_key_mappings", mapping_data)

    ASSETS.save_loaded_asset(action, only_if_is_dirty=False)
    ASSETS.save_loaded_asset(context, only_if_is_dirty=False)
    log("IA_Interact and IMC_Prototype (E) ready")


def ensure_component_blueprint():
    blueprint = ensure_blueprint(COMPONENT_PATH, unreal.ActorComponent)
    graph_names = {str(name) for name in unreal.BlueprintEditorLibrary.list_graph_names(blueprint)}
    double_type = unreal.BlueprintEditorLibrary.get_basic_type_by_name("real")
    actor_type = unreal.BlueprintEditorLibrary.get_object_reference_type(unreal.Actor.static_class())

    if "InteractionDistance" not in unreal.BlueprintEditorLibrary.list_member_variable_names(blueprint):
        if not unreal.BlueprintEditorLibrary.add_member_variable(blueprint, "InteractionDistance", double_type):
            raise RuntimeError("Could not add InteractionDistance")
    if "FocusedActor" not in unreal.BlueprintEditorLibrary.list_member_variable_names(blueprint):
        if not unreal.BlueprintEditorLibrary.add_member_variable(blueprint, "FocusedActor", actor_type):
            raise RuntimeError("Could not add FocusedActor")
    unreal.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(
        blueprint, "InteractionDistance", True
    )

    for function_name in ("TraceForInteractable", "UpdateFocus", "TryInteract"):
        if function_name not in graph_names:
            unreal.BlueprintEditorLibrary.add_function_graph(blueprint, function_name)

    trace_graph = unreal.BlueprintEditorLibrary.find_graph(blueprint, unreal.Name("TraceForInteractable"))
    trace_editor = unreal.BlueprintGraphEditor.get_graph_editor(trace_graph)
    result_node = next(
        (node for node in trace_editor.list_all_nodes() if isinstance(node, unreal.K2Node_FunctionResult)),
        None,
    )
    output_names = {
        str(unreal.BlueprintGraphPinLibrary.get_pin_name(pin))
        for pin in (unreal.BlueprintEditorLibrary.list_input_pins(result_node) if result_node else [])
    }
    # Function return pins are added through the graph editor as output parameters.
    if "InteractableActor" not in output_names:
        trace_editor.add_graph_output_parameter("InteractableActor", actor_type)

    dispatchers = {str(name) for name in unreal.BlueprintEditorLibrary.list_event_dispatchers(blueprint)}
    if "OnFocusedActorChanged" not in dispatchers:
        unreal.BlueprintEditorLibrary.add_event_dispatcher(blueprint, "OnFocusedActorChanged")
        unreal.BlueprintEditorLibrary.add_event_dispatcher_parameter(
            blueprint, "OnFocusedActorChanged", "FocusedActor", actor_type
        )

    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    cdo = unreal.get_default_object(blueprint.generated_class())
    cdo.set_editor_property("InteractionDistance", 300.0)
    cdo.set_editor_property("auto_activate", True)
    try:
        tick = cdo.get_editor_property("primary_component_tick")
        tick.set_editor_property("tick_interval", 0.05)
        tick.set_editor_property("can_ever_tick", True)
        cdo.set_editor_property("primary_component_tick", tick)
    except Exception as exc:
        log(f"Tick struct will be configured in graph if needed: {exc}")
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    ASSETS.save_loaded_asset(blueprint, only_if_is_dirty=False)
    log("BPC_Interaction shell, variables, functions, and dispatcher ready")
    return blueprint


def ensure_box_blueprint():
    from editor_toolset.toolsets.actor import ActorTools

    blueprint = ensure_blueprint(BOX_PATH, unreal.Actor)
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    cdo = unreal.get_default_object(blueprint.generated_class())
    mesh_component = cdo.get_component_by_class(unreal.SkeletalMeshComponent)
    if mesh_component is None:
        mesh_component = ActorTools.add_component(
            blueprint, unreal.SkeletalMeshComponent.static_class(), "CrateMesh"
        )
    crate_mesh = require_asset("/Game/AnimatedWoodenCrateV1/Meshes/SKM_WoodenCrate")
    try:
        mesh_component.set_skeletal_mesh_asset(crate_mesh)
    except Exception:
        mesh_component.set_editor_property("skeletal_mesh_asset", crate_mesh)
    mesh_component.set_collision_profile_name("BlockAllDynamic")
    mesh_component.set_editor_property("generate_overlap_events", True)
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    ASSETS.save_loaded_asset(blueprint, only_if_is_dirty=False)
    log("BP_AnomalyBox shell and crate mesh ready")
    return blueprint


def ensure_character_component(component_blueprint):
    from editor_toolset.toolsets.actor import ActorTools

    character = require_asset(CHARACTER_PATH)
    unreal.BlueprintEditorLibrary.compile_blueprint(component_blueprint)
    component_class = component_blueprint.generated_class()
    unreal.BlueprintEditorLibrary.compile_blueprint(character)
    character_cdo = unreal.get_default_object(character.generated_class())
    component = character_cdo.get_component_by_class(component_class)
    if component is None:
        component = ActorTools.add_component(character, component_class, "BPC_Interaction")
    unreal.BlueprintEditorLibrary.compile_blueprint(character)
    ASSETS.save_loaded_asset(character, only_if_is_dirty=False)
    log("BPC_Interaction added to BP_FirstPersonCharacter")


def ensure_box_placed(box_blueprint):
    if not LEVELS.load_level(MAP_PATH):
        raise RuntimeError("Could not load L_Prototype")
    box_class = box_blueprint.generated_class()
    existing = None
    for actor in ACTORS.get_all_level_actors():
        if actor.get_actor_label() == "PROTOTYPE_AnomalyBox_T01":
            existing = actor
            break
    if existing is None:
        existing = ACTORS.spawn_actor_from_class(
            box_class, unreal.Vector(0.0, 0.0, 85.0), unreal.Rotator(0.0, 0.0, 0.0), transient=False
        )
        if existing is None:
            raise RuntimeError("Could not place BP_AnomalyBox")
        existing.set_actor_label("PROTOTYPE_AnomalyBox_T01")
    if not LEVELS.save_current_level():
        raise RuntimeError("Could not save L_Prototype")
    log("BP_AnomalyBox placed on central pedestal")


def main():
    ensure_interface_signature()
    ensure_input_assets()
    component_blueprint = ensure_component_blueprint()
    box_blueprint = ensure_box_blueprint()
    ensure_character_component(component_blueprint)
    ensure_box_placed(box_blueprint)
    log("BASE BUILD PASS")


main()
