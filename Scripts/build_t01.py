"""Build T01 interaction assets with Unreal Editor's official Python API.

Run inside Unreal Editor 5.8 (Output Log set to Python):
    exec(open(r'F:/AnomalyLab/我的项目3/Scripts/build_t01.py', encoding='utf-8').read())

This script deliberately does not use the HTTP/MCP bridge.  It is idempotent for
the nodes it owns and preserves the First Person template's existing input graph.
"""

import unreal

from editor_toolset.toolsets.actor import ActorTools
from editor_toolset.toolsets.blueprint import BlueprintTools


PREFIX = "[T01]"
TAG = "T01_GENERATED"

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
CONTROLLER_PATH = "/Game/FirstPerson/Blueprints/BP_FirstPersonPlayerController"
MAP_PATH = "/Game/Prototype/Maps/L_Prototype"
CRATE_PATH = "/Game/AnimatedWoodenCrateV1/Meshes/SKM_WoodenCrate"


def log(message):
    unreal.log(f"{PREFIX} {message}")


def fail(message):
    raise RuntimeError(f"{PREFIX} {message}")


def load(path):
    asset = ASSETS.load_asset(path)
    if asset is None:
        fail(f"Missing asset: {path}")
    return asset


def compile_and_save(blueprint):
    BlueprintTools.compile_blueprint(blueprint, warnings_as_errors=False)
    if not ASSETS.save_loaded_asset(blueprint, only_if_is_dirty=False):
        fail(f"Could not save {blueprint.get_path_name()}")


def graph(blueprint, name):
    result = unreal.BlueprintEditorLibrary.find_graph(blueprint, unreal.Name(name))
    if result is None:
        fail(f"Graph {name} missing in {blueprint.get_path_name()}")
    return result


def input_pins(node):
    return list(unreal.BlueprintEditorLibrary.list_input_pins(node))


def output_pins(node):
    return list(unreal.BlueprintEditorLibrary.list_output_pins(node))


def pin_name(pin):
    return str(unreal.BlueprintGraphPinLibrary.get_pin_name(pin))


def norm(value):
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def find_pin(node, direction, aliases, required=True):
    candidates = input_pins(node) if direction == "in" else output_pins(node)
    aliases = [norm(item) for item in aliases]
    for candidate in candidates:
        if norm(pin_name(candidate)) in aliases:
            return candidate
    for candidate in candidates:
        candidate_name = norm(pin_name(candidate))
        if any(alias in candidate_name or candidate_name in alias for alias in aliases):
            return candidate
    if required:
        names = [pin_name(item) for item in candidates]
        fail(f"Pin {aliases} not found on {node.get_node_title()}; available={names}")
    return None


def connect(out_node, out_names, in_node, in_names):
    source = find_pin(out_node, "out", out_names)
    target = find_pin(in_node, "in", in_names)
    if not source.try_create_connection(target):
        fail(
            f"Could not connect {out_node.get_node_title()}.{pin_name(source)} -> "
            f"{in_node.get_node_title()}.{pin_name(target)}"
        )


def set_default(node, aliases, value):
    target = find_pin(node, "in", aliases)
    if not target.set_pin_value(str(value)):
        fail(f"Could not set {node.get_node_title()}.{pin_name(target)}={value}")


def node_type(
    graph_obj, searches, include=(), exclude=(), pin_words=(),
    input_words=(), output_words=(), forbidden_input_words=(),
):
    include = tuple(norm(item) for item in include)
    exclude = tuple(norm(item) for item in exclude)
    pin_words = tuple(norm(item) for item in pin_words)
    input_words = tuple(norm(item) for item in input_words)
    output_words = tuple(norm(item) for item in output_words)
    forbidden_input_words = tuple(norm(item) for item in forbidden_input_words)
    seen = []
    for search in searches:
        for candidate in BlueprintTools.find_node_types(graph_obj, search):
            if candidate in seen:
                continue
            seen.append(candidate)
            lowered = norm(candidate)
            if include and not all(item in lowered for item in include):
                continue
            if any(item in lowered for item in exclude):
                continue
            if pin_words or input_words or output_words or forbidden_input_words:
                try:
                    info = BlueprintTools.get_node_type_pins(graph_obj, candidate)
                    input_names = {norm(item.name) for item in info.input_pins}
                    output_names = {norm(item.name) for item in info.output_pins}
                    names = input_names | output_names
                    if not all(any(word in name or name in word for name in names) for word in pin_words):
                        continue
                    if not all(any(word in name or name in word for name in input_names) for word in input_words):
                        continue
                    if not all(any(word in name or name in word for name in output_names) for word in output_words):
                        continue
                    if any(any(word in name or name in word for name in input_names)
                           for word in forbidden_input_words):
                        continue
                except Exception:
                    continue
            return candidate
    fail(
        f"No node type matched searches={searches}, include={include}, "
        f"exclude={exclude}, candidates={seen[:30]}"
    )


def create(
    graph_obj, searches, x, y, include=(), exclude=(), pin_words=(),
    input_words=(), output_words=(), forbidden_input_words=(),
):
    type_id = node_type(
        graph_obj, searches, include, exclude, pin_words,
        input_words, output_words, forbidden_input_words,
    )
    result = BlueprintTools.create_node(graph_obj, type_id, unreal.IntPoint(x, y))
    try:
        result.set_editor_property("node_comment", TAG)
    except Exception:
        pass
    return result


def clear_function_body(graph_obj):
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph_obj)
    stale = [
        node
        for node in editor.list_all_nodes()
        if not isinstance(node, (unreal.K2Node_FunctionEntry, unreal.K2Node_FunctionResult))
    ]
    if stale:
        editor.remove_nodes(stale)


def clear_owned_event_nodes(graph_obj):
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph_obj)
    stale = []
    for node in editor.list_all_nodes():
        try:
            if str(node.get_editor_property("node_comment")) == TAG:
                stale.append(node)
        except Exception:
            continue
    if stale:
        editor.remove_nodes(stale)


def entry_and_result(graph_obj):
    nodes = unreal.BlueprintGraphEditor.get_graph_editor(graph_obj).list_all_nodes()
    entry = next((node for node in nodes if isinstance(node, unreal.K2Node_FunctionEntry)), None)
    result = next((node for node in nodes if isinstance(node, unreal.K2Node_FunctionResult)), None)
    if entry is None or result is None:
        fail(f"Function graph {graph_obj.get_name()} lacks entry/result nodes")
    return entry, result


def ensure_interface_signature():
    bpi = load(BPI_PATH)
    names = {str(item) for item in unreal.BlueprintEditorLibrary.list_graph_names(bpi)}
    interact = (
        unreal.BlueprintEditorLibrary.add_function_graph(bpi, "Interact")
        if "Interact" not in names
        else graph(bpi, "Interact")
    )
    editor = unreal.BlueprintGraphEditor.get_graph_editor(interact)
    entry = next(node for node in editor.list_all_nodes() if isinstance(node, unreal.K2Node_FunctionEntry))
    if not any(pin_name(pin) == "Interactor" for pin in output_pins(entry)):
        actor_type = unreal.BlueprintEditorLibrary.get_object_reference_type(unreal.Actor.static_class())
        if not editor.add_graph_input_parameter("Interactor", actor_type, ""):
            fail("Could not add BPI_Interactable.Interact Interactor parameter")
    editor.set_function_is_public()
    compile_and_save(bpi)
    return bpi


def interface_class(interface_blueprint):
    result = interface_blueprint.generated_class()
    if result is None:
        compile_and_save(interface_blueprint)
        result = interface_blueprint.generated_class()
    if result is None:
        fail("BPI_Interactable generated class unavailable")
    return result


def class_implements(object_or_class, interface):
    try:
        return bool(unreal.SystemLibrary.does_implement_interface(object_or_class, interface))
    except Exception:
        try:
            return bool(object_or_class.implements_interface(interface))
        except Exception:
            return False


def add_blueprint_interface(blueprint, interface_blueprint):
    iface = interface_class(interface_blueprint)
    compile_and_save(blueprint)
    if class_implements(unreal.get_default_object(blueprint.generated_class()), iface):
        return

    # API names changed across UE branches; use whichever official reflected call exists.
    for owner in (unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor):
        for method_name in ("add_interface", "add_implemented_interface", "implement_interface"):
            method = getattr(owner, method_name, None)
            if callable(method):
                for argument in (interface_blueprint, iface):
                    try:
                        method(blueprint, argument)
                        compile_and_save(blueprint)
                        if class_implements(unreal.get_default_object(blueprint.generated_class()), iface):
                            return
                    except Exception:
                        pass

    # FBPInterfaceDescription is exposed as BPInterfaceDescription on builds that
    # allow Python mutation of UBlueprint.  Do not continue if the property is locked.
    description_class = getattr(unreal, "BPInterfaceDescription", None)
    if description_class is not None:
        try:
            current = list(blueprint.get_editor_property("implemented_interfaces"))
            description = description_class()
            description.set_editor_property("interface", iface)
            current.append(description)
            blueprint.set_editor_property("implemented_interfaces", current)
            compile_and_save(blueprint)
        except Exception as exc:
            log(f"Reflected interface property unavailable: {exc}")

    if not class_implements(unreal.get_default_object(blueprint.generated_class()), iface):
        fail(
            "UE 5.8 did not expose a writable Blueprint interface API. No graph assets were "
            "rewritten. Add BPI_Interactable to BP_AnomalyBox once in Class Settings, then rerun."
        )


def ensure_input_assets():
    action = ASSETS.load_asset(ACTION_PATH)
    if action is None:
        factory_type = getattr(unreal, "InputAction_Factory", None)
        action = ASSET_TOOLS.create_asset(
            "IA_Interact", "/Game/Core/Input", unreal.InputAction,
            factory_type() if factory_type else None,
        )
    action.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)

    context = ASSETS.load_asset(CONTEXT_PATH)
    if context is None:
        factory_type = getattr(unreal, "InputMappingContext_Factory", None)
        context = ASSET_TOOLS.create_asset(
            "IMC_Prototype", "/Game/Core/Input", unreal.InputMappingContext,
            factory_type() if factory_type else None,
        )
    key = unreal.Key()
    key.set_editor_property("key_name", unreal.Name("E"))
    mapping = unreal.EnhancedActionKeyMapping()
    mapping.set_editor_property("action", action)
    mapping.set_editor_property("key", key)
    data = unreal.InputMappingContextMappingData()
    data.set_editor_property("mappings", [mapping])
    context.set_editor_property("default_key_mappings", data)
    ASSETS.save_loaded_asset(action, only_if_is_dirty=False)
    ASSETS.save_loaded_asset(context, only_if_is_dirty=False)
    return action, context


def ensure_blueprint_shells():
    component = ASSETS.load_asset(COMPONENT_PATH)
    if component is None:
        component = unreal.BlueprintEditorLibrary.create_blueprint_asset_with_parent(
            COMPONENT_PATH, unreal.ActorComponent
        )
    box = ASSETS.load_asset(BOX_PATH)
    if box is None:
        box = unreal.BlueprintEditorLibrary.create_blueprint_asset_with_parent(BOX_PATH, unreal.Actor)
    if component is None or box is None:
        fail("Could not create T01 Blueprint shells")

    actor_type = unreal.BlueprintEditorLibrary.get_object_reference_type(unreal.Actor.static_class())
    real_type = unreal.BlueprintEditorLibrary.get_basic_type_by_name("real")
    variables = {str(item) for item in unreal.BlueprintEditorLibrary.list_member_variable_names(component)}
    if "InteractionDistance" not in variables:
        unreal.BlueprintEditorLibrary.add_member_variable(component, "InteractionDistance", real_type)
    if "FocusedActor" not in variables:
        unreal.BlueprintEditorLibrary.add_member_variable(component, "FocusedActor", actor_type)
    unreal.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(
        component, "InteractionDistance", True
    )
    graph_names = {str(item) for item in unreal.BlueprintEditorLibrary.list_graph_names(component)}
    for function_name in ("TraceForInteractable", "UpdateFocus", "TryInteract"):
        if function_name not in graph_names:
            unreal.BlueprintEditorLibrary.add_function_graph(component, function_name)
    trace = graph(component, "TraceForInteractable")
    trace_editor = unreal.BlueprintGraphEditor.get_graph_editor(trace)
    result = next(
        node for node in trace_editor.list_all_nodes() if isinstance(node, unreal.K2Node_FunctionResult)
    )
    if not any(pin_name(pin) == "InteractableActor" for pin in input_pins(result)):
        trace_editor.add_graph_output_parameter("InteractableActor", actor_type)
    dispatchers = {str(item) for item in unreal.BlueprintEditorLibrary.list_event_dispatchers(component)}
    if "OnFocusedActorChanged" not in dispatchers:
        unreal.BlueprintEditorLibrary.add_event_dispatcher(component, "OnFocusedActorChanged")
        unreal.BlueprintEditorLibrary.add_event_dispatcher_parameter(
            component, "OnFocusedActorChanged", "FocusedActor", actor_type
        )
    compile_and_save(component)
    cdo = unreal.get_default_object(component.generated_class())
    cdo.set_editor_property("InteractionDistance", 300.0)
    try:
        cdo.set_component_tick_interval(0.05)
        cdo.set_component_tick_enabled(True)
    except Exception as exc:
        log(f"Tick methods unavailable; Event Tick still enables ticking: {exc}")
    compile_and_save(component)
    return component, box


def build_trace_graph(component, bpi):
    target = graph(component, "TraceForInteractable")
    clear_function_body(target)
    entry, result = entry_and_result(target)

    owner = create(target, ["GetOwner"], -1750, -150, include=("getowner",))
    get_component = create(
        target, ["GetComponentByClass"], -1500, -150,
        include=("getcomponentbyclass",), pin_words=("ComponentClass", "ReturnValue"),
    )
    set_default(get_component, ["ComponentClass"], "/Script/Engine.CameraComponent")
    cast_camera = create(target, ["CastToCameraComponent"], -1250, -150, include=("cast", "camera"))
    world_location = create(target, ["GetWorldLocation"], -1000, -350, include=("getworldlocation",))
    forward = create(target, ["GetForwardVector"], -1000, -50, include=("getforwardvector",))
    distance = create(
        target, ["InteractionDistance"], -1000, 250,
        include=("interactiondistance",), output_words=("InteractionDistance",),
        forbidden_input_words=("InteractionDistance", "self"),
    )
    multiply = create(
        target, ["工具|运算符|乘", "Multiply", "乘"], -700, 0,
        exclude=("matrix", "rotator", "int", "byte"),
    )
    add = create(
        target, ["工具|运算符|添加", "Add", "加"], -450, -150,
        exclude=("matrix", "rotator", "int", "byte", "string"),
    )
    trace = create(
        target, ["LineTraceByChannel", "LineTraceSingle"], -150, -150,
        include=("linetrace",), exclude=("multi", "sphere", "box", "capsule"),
        pin_words=("Start", "End", "OutHit"),
    )
    break_hit = create(target, ["BreakHitResult"], 100, 150, include=("breakhitresult",))
    implements = create(
        target, ["DoesObjectImplementInterface", "DoesImplementInterface"], 350, 150,
        include=("implementinterface",),
    )
    select = create(target, ["工具|选择", "Select", "选择"], 600, 50, exclude=("selectclass",))

    connect(entry, ["then"], cast_camera, ["execute", "exec"])
    connect(owner, ["returnvalue", "owner"], get_component, ["target", "self"])
    connect(get_component, ["returnvalue", "component"], cast_camera, ["object"])
    connect(cast_camera, ["then"], trace, ["execute", "exec"])
    connect(cast_camera, ["ascameracomponent", "as", "result"], world_location, ["target", "self"])
    connect(cast_camera, ["ascameracomponent", "as", "result"], forward, ["target", "self"])
    connect(forward, ["returnvalue", "forwardvector"], multiply, ["a", "vector", "input"])
    connect(distance, ["interactiondistance", "value"], multiply, ["b", "scale", "float"])
    connect(world_location, ["returnvalue", "location"], add, ["a", "vectora"])
    connect(multiply, ["returnvalue", "result"], add, ["b", "vectorb"])
    connect(world_location, ["returnvalue", "location"], trace, ["start"])
    connect(add, ["returnvalue", "result"], trace, ["end"])
    set_default(trace, ["TraceChannel"], "TraceTypeQuery1")
    set_default(trace, ["bTraceComplex", "TraceComplex"], "false")
    set_default(trace, ["DrawDebugType"], "None")
    set_default(trace, ["bIgnoreSelf", "IgnoreSelf"], "true")
    connect(trace, ["then"], result, ["execute", "exec"])
    connect(cast_camera, ["castfailed", "failed"], result, ["execute", "exec"])
    connect(trace, ["outhit", "hit"], break_hit, ["inhit", "hit"])
    connect(break_hit, ["hitactor", "actor"], implements, ["testobject", "object"])
    set_default(
        implements, ["Interface"],
        f"{BPI_PATH}.{bpi.get_name()}_C",
    )
    # Connect Actor first so the wildcard Select node promotes to Actor reference.
    connect(break_hit, ["hitactor", "actor"], select, ["a", "option0"])
    connect(implements, ["returnvalue", "result"], select, ["picka", "index", "condition"])
    connect(select, ["returnvalue", "result"], result, ["interactableactor"])
    BlueprintTools.arrange_nodes(BlueprintTools.find_nodes(target))


def build_update_focus_graph(component):
    target = graph(component, "UpdateFocus")
    clear_function_body(target)
    entry, result = entry_and_result(target)
    trace = create(target, ["TraceForInteractable"], -900, 0, include=("traceforinteractable",))
    get_focus = create(
        target, ["FocusedActor"], -650, 200, include=("focusedactor",),
        output_words=("FocusedActor",), forbidden_input_words=("FocusedActor", "self"),
    )
    not_equal = create(
        target, ["工具|运算符|不等于（!=）", "NotEqual", "不等于"], -400, 100,
        exclude=("string", "name", "text", "vector", "int", "float"),
    )
    branch = create(target, ["工具|流程控制|分支", "Branch", "分支"], -150, 0)
    set_focus = create(
        target, ["FocusedActor"], 100, -100, include=("focusedactor",),
        input_words=("execute", "FocusedActor"), output_words=("then",),
    )
    dispatcher = create(
        target, ["OnFocusedActorChanged"], 350, -100,
        include=("callonfocusedactorchanged",),
    )
    printer = create(target, ["Development|PrintString", "PrintString"], 600, -100, include=("printstring",))
    set_default(printer, ["InString", "String"], "[Interaction] Focus changed")
    set_default(printer, ["PrintToScreen"], "false")
    set_default(printer, ["PrintToLog"], "true")

    connect(entry, ["then"], trace, ["execute", "exec"])
    connect(trace, ["then"], branch, ["execute", "exec"])
    connect(trace, ["interactableactor", "returnvalue"], not_equal, ["a"])
    connect(get_focus, ["focusedactor", "value"], not_equal, ["b"])
    connect(not_equal, ["returnvalue", "result"], branch, ["condition"])
    connect(branch, ["true", "then"], set_focus, ["execute", "exec"])
    connect(trace, ["interactableactor", "returnvalue"], set_focus, ["focusedactor", "value"])
    connect(set_focus, ["then"], dispatcher, ["execute", "exec"])
    connect(trace, ["interactableactor", "returnvalue"], dispatcher, ["focusedactor"])
    connect(dispatcher, ["then"], printer, ["execute", "exec"])
    connect(printer, ["then"], result, ["execute", "exec"])
    connect(branch, ["false", "else"], result, ["execute", "exec"])
    BlueprintTools.arrange_nodes(BlueprintTools.find_nodes(target))


def build_try_interact_graph(component):
    target = graph(component, "TryInteract")
    clear_function_body(target)
    entry, result = entry_and_result(target)
    trace = create(target, ["TraceForInteractable"], -900, 0, include=("traceforinteractable",))
    valid = create(
        target, ["Utilities|IsValid", "IsValid"], -600, 0, include=("isvalid",),
        input_words=("execute",), output_words=("IsValid", "IsNotValid"),
    )
    message = create(
        target, ["Interact"], -300, -150,
        include=("interact", "message"), exclude=("event", "input", "dispatcher"),
    )
    owner = create(target, ["GetOwner"], -300, 150, include=("getowner",))
    valid_log = create(target, ["Development|PrintString", "PrintString"], 0, -150, include=("printstring",))
    reject_log = create(target, ["Development|PrintString", "PrintString"], 0, 150, include=("printstring",))
    for printer, message_text in (
        (valid_log, "[Interaction] Valid interface call"),
        (reject_log, "[Interaction] Rejected interaction"),
    ):
        set_default(printer, ["InString", "String"], message_text)
        set_default(printer, ["PrintToScreen"], "false")
        set_default(printer, ["PrintToLog"], "true")

    connect(entry, ["then"], trace, ["execute", "exec"])
    connect(trace, ["then"], valid, ["execute", "exec"])
    connect(trace, ["interactableactor", "returnvalue"], valid, ["inputobject", "object"])
    connect(valid, ["isvalid", "valid"], message, ["execute", "exec"])
    connect(valid, ["isnotvalid", "notvalid", "invalid"], reject_log, ["execute", "exec"])
    connect(trace, ["interactableactor", "returnvalue"], message, ["target", "self"])
    connect(owner, ["returnvalue", "owner"], message, ["interactor"])
    connect(message, ["then"], valid_log, ["execute", "exec"])
    connect(valid_log, ["then"], result, ["execute", "exec"])
    connect(reject_log, ["then"], result, ["execute", "exec"])
    BlueprintTools.arrange_nodes(BlueprintTools.find_nodes(target))


def build_component_events(component):
    target = unreal.BlueprintEditorLibrary.find_event_graph(component)
    clear_owned_event_nodes(target)
    tick = create(target, ["AddEvent|EventTick", "EventTick"], -400, 0, include=("eventtick",))
    update = create(target, ["UpdateFocus"], -100, 0, include=("updatefocus",))
    connect(tick, ["then"], update, ["execute", "exec"])


def ensure_box_mesh(box):
    compile_and_save(box)
    cdo = unreal.get_default_object(box.generated_class())
    components = list(cdo.get_components_by_class(unreal.SkeletalMeshComponent))
    mesh_component = next((item for item in components if item.get_name() == "CrateMesh"), None)
    if mesh_component is None:
        mesh_component = ActorTools.add_component(box, unreal.SkeletalMeshComponent.static_class(), "CrateMesh")
    for extra in components:
        if extra != mesh_component:
            try:
                ActorTools.remove_component(extra)
            except Exception as exc:
                log(f"Could not remove duplicate mesh component {extra.get_name()}: {exc}")
    crate = load(CRATE_PATH)
    try:
        mesh_component.set_skeletal_mesh_asset(crate)
    except Exception:
        mesh_component.set_editor_property("skeletal_mesh_asset", crate)
    mesh_component.set_collision_profile_name("BlockAllDynamic")
    mesh_component.set_editor_property("generate_overlap_events", True)


def build_box_event(box):
    target = unreal.BlueprintEditorLibrary.find_event_graph(box)
    clear_owned_event_nodes(target)
    event = create(
        target, ["AddEvent|Interact", "Interact"], -500, 0,
        include=("interact",), exclude=("message", "input"),
    )
    display_name = create(target, ["GetDisplayName"], -250, 150, include=("getdisplayname",))
    printer = create(target, ["Development|PrintString", "PrintString"], 0, 0, include=("printstring",))
    append = create(target, ["Concat_StrStr", "Concat"], -100, 150, exclude=("array", "vector"))
    set_default(append, ["a"], "[Interaction] BP_AnomalyBox Interact by ")
    connect(event, ["interactor"], display_name, ["object"])
    connect(display_name, ["returnvalue", "displayname"], append, ["b"])
    connect(event, ["then"], printer, ["execute", "exec"])
    connect(append, ["returnvalue", "result"], printer, ["instring", "string"])
    set_default(printer, ["PrintToScreen"], "false")
    set_default(printer, ["PrintToLog"], "true")


def ensure_character_component(character, component):
    compile_and_save(component)
    compile_and_save(character)
    cdo = unreal.get_default_object(character.generated_class())
    component_class = component.generated_class()
    instance = cdo.get_component_by_class(component_class)
    if instance is None:
        instance = ActorTools.add_component(character, component_class, "BPC_Interaction")
    compile_and_save(character)
    return instance


def existing_type_id(blueprint, title_terms):
    target = unreal.BlueprintEditorLibrary.find_event_graph(blueprint)
    for node in BlueprintTools.find_nodes(target):
        info = BlueprintTools._get_node_info(node)
        haystack = norm(f"{info.type_id} {node.get_node_title()}")
        if all(norm(term) in haystack for term in title_terms):
            return info.type_id
    return None


def build_controller_context(controller):
    target = unreal.BlueprintEditorLibrary.find_event_graph(controller)
    tagged = []
    for node in BlueprintTools.find_nodes(target):
        try:
            if str(node.get_editor_property("node_comment")) == TAG:
                tagged.append(node)
        except Exception:
            pass
    if tagged:
        log("IMC_Prototype mapping-context node already exists in PlayerController")
        return

    source_add = None
    source_subsystem_pin = None
    for node in BlueprintTools.find_nodes(target):
        info = BlueprintTools._get_node_info(node)
        if "addmappingcontext" not in norm(f"{info.type_id} {node.get_node_title()}"):
            continue
        self_pin = find_pin(node, "in", ["self", "target"], required=False)
        if self_pin is None:
            continue
        linked = list(self_pin.list_connected_pins())
        if linked:
            source_add = node
            source_subsystem_pin = linked[0]
            break
    if source_add is None or source_subsystem_pin is None:
        fail("Could not find the template's existing AddMappingContext/subsystem chain")

    add_type = BlueprintTools._get_node_info(source_add).type_id
    add_context = BlueprintTools.create_node(target, add_type, unreal.IntPoint(0, 0))
    add_context.set_editor_property("node_comment", TAG)
    set_default(add_context, ["MappingContext"], f"{CONTEXT_PATH}.IMC_Prototype")
    set_default(add_context, ["Priority"], "1")
    subsystem_target = find_pin(add_context, "in", ["self", "target"])
    if not source_subsystem_pin.try_create_connection(subsystem_target):
        fail("Could not reuse the Enhanced Input subsystem for IMC_Prototype")

    old_then = find_pin(source_add, "out", ["then"])
    downstream = list(old_then.list_connected_pins())
    for downstream_pin in downstream:
        old_then.break_single_pin_link(downstream_pin)
    new_exec = find_pin(add_context, "in", ["execute", "exec"])
    if not old_then.try_create_connection(new_exec):
        fail("Could not chain IMC_Prototype after the existing mapping context")
    new_then = find_pin(add_context, "out", ["then"])
    for downstream_pin in downstream:
        if not new_then.try_create_connection(downstream_pin):
            fail("Could not restore PlayerController BeginPlay downstream execution")
    BlueprintTools.arrange_nodes([source_add, add_context])


def build_character_events(character):
    target = unreal.BlueprintEditorLibrary.find_event_graph(character)
    clear_owned_event_nodes(target)
    input_event = create(
        target, ["IA_Interact"], -500, 250,
        include=("ia_interact",), exclude=("get", "mapping"), pin_words=("Started",),
    )
    component_getter = create(
        target, ["BPCInteraction", "BPC_Interaction"], -250, 450,
        include=("bpcinteraction",), output_words=("BPCInteraction",),
        forbidden_input_words=("BPCInteraction", "self"),
    )
    try_interact = create(target, ["TryInteract"], 0, 250, include=("tryinteract",))
    connect(input_event, ["started"], try_interact, ["execute", "exec"])
    connect(component_getter, ["bpcinteraction", "value", "returnvalue"], try_interact, ["target", "self"])


def place_box(box):
    if not LEVELS.load_level(MAP_PATH):
        fail("Could not load L_Prototype")
    existing = next(
        (actor for actor in ACTORS.get_all_level_actors() if actor.get_actor_label() == "PROTOTYPE_AnomalyBox_T01"),
        None,
    )
    if existing is None:
        existing = ACTORS.spawn_actor_from_class(
            box.generated_class(), unreal.Vector(0.0, 0.0, 85.0), unreal.Rotator(), transient=False
        )
        if existing is None:
            fail("Could not place BP_AnomalyBox")
        existing.set_actor_label("PROTOTYPE_AnomalyBox_T01")
    if not LEVELS.save_current_level():
        fail("Could not save L_Prototype")


def main():
    log("Starting official-Python T01 build")
    bpi = ensure_interface_signature()
    ensure_input_assets()
    component, box = ensure_blueprint_shells()

    # Interface capability is checked before destructive graph rebuilds.
    add_blueprint_interface(box, bpi)
    build_trace_graph(component, bpi)
    build_update_focus_graph(component)
    build_try_interact_graph(component)
    build_component_events(component)
    compile_and_save(component)

    ensure_box_mesh(box)
    build_box_event(box)
    compile_and_save(box)

    character = load(CHARACTER_PATH)
    controller = load(CONTROLLER_PATH)
    ensure_character_component(character, component)
    build_controller_context(controller)
    compile_and_save(controller)
    build_character_events(character)
    compile_and_save(character)
    place_box(box)
    log("BUILD PASS - run validate_t01.py next")


main()
