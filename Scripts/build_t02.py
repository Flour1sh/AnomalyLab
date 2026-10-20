"""Build the T02 Anomaly Box entirely through Unreal's in-process Python API.

This script does not use the HTTP/MCP bridge and does not start PIE. It is
idempotent for the EventGraph nodes tagged T02_GENERATED.
"""

import unreal

from editor_toolset.toolsets.actor import ActorTools
from editor_toolset.toolsets.blueprint import BlueprintTools


PREFIX = "[T02]"
TAG = "T02_GENERATED"
BOX_PATH = "/Game/Anomalies/Containers/BP_AnomalyBox"
OUTCOME_PATH = "/Game/Core/Types/EAnomalyOutcome"
OPEN_ANIM_PATH = "/Game/AnimatedWoodenCrateV1/Animations/AS_WoodenCrateOpen"
OPEN_SOUND_PATH = "/Game/AnimatedWoodenCrateV1/Audio/SC_WoodenCrateOpen"

ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)


def log(message):
    unreal.log(f"{PREFIX} {message}")


def fail(message):
    raise RuntimeError(f"{PREFIX} {message}")


def load(path):
    asset = ASSETS.load_asset(path)
    if asset is None:
        fail(f"Missing required asset: {path}")
    return asset


def norm(value):
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def input_pins(node):
    return list(unreal.BlueprintEditorLibrary.list_input_pins(node))


def output_pins(node):
    return list(unreal.BlueprintEditorLibrary.list_output_pins(node))


def pin_name(pin):
    return str(unreal.BlueprintGraphPinLibrary.get_pin_name(pin))


def find_pin(node, direction, aliases, required=True):
    pins = input_pins(node) if direction == "in" else output_pins(node)
    wanted = [norm(item) for item in aliases]
    for pin in pins:
        if norm(pin_name(pin)) in wanted:
            return pin
    for pin in pins:
        candidate = norm(pin_name(pin))
        if any(item in candidate or candidate in item for item in wanted):
            return pin
    if required:
        fail(f"Pin {aliases} missing on {node.get_node_title()}; available={[pin_name(p) for p in pins]}")
    return None


def connect(out_node, out_aliases, in_node, in_aliases):
    source = find_pin(out_node, "out", out_aliases)
    target = find_pin(in_node, "in", in_aliases)
    if not source.try_create_connection(target):
        fail(
            f"Could not connect {out_node.get_node_title()}.{pin_name(source)} -> "
            f"{in_node.get_node_title()}.{pin_name(target)}"
        )


def set_default(node, aliases, value):
    pin = find_pin(node, "in", aliases)
    if not pin.set_pin_value(str(value)):
        fail(f"Could not set {node.get_node_title()}.{pin_name(pin)}={value}")


def node_type(graph, searches, include=(), exclude=(), pin_words=(), input_words=(), output_words=()):
    include = tuple(norm(item) for item in include)
    exclude = tuple(norm(item) for item in exclude)
    pin_words = tuple(norm(item) for item in pin_words)
    input_words = tuple(norm(item) for item in input_words)
    output_words = tuple(norm(item) for item in output_words)
    seen = []
    for search in searches:
        for candidate in BlueprintTools.find_node_types(graph, search):
            if candidate in seen:
                continue
            seen.append(candidate)
            lowered = norm(candidate)
            if include and not all(item in lowered for item in include):
                continue
            if any(item in lowered for item in exclude):
                continue
            if pin_words or input_words or output_words:
                try:
                    info = BlueprintTools.get_node_type_pins(graph, candidate)
                    inputs = {norm(item.name) for item in info.input_pins}
                    outputs = {norm(item.name) for item in info.output_pins}
                    both = inputs | outputs
                    if not all(any(word in name or name in word for name in both) for word in pin_words):
                        continue
                    if not all(any(word in name or name in word for name in inputs) for word in input_words):
                        continue
                    if not all(any(word in name or name in word for name in outputs) for word in output_words):
                        continue
                except Exception:
                    continue
            return candidate
    fail(f"No node type matched {searches}; candidates={seen[:40]}")


def create(graph, searches, x, y, include=(), exclude=(), pin_words=(), input_words=(), output_words=()):
    type_id = node_type(graph, searches, include, exclude, pin_words, input_words, output_words)
    node = BlueprintTools.create_node(graph, type_id, unreal.IntPoint(x, y))
    try:
        node.set_editor_property("node_comment", TAG)
    except Exception:
        pass
    return node


def compile_and_save(blueprint):
    BlueprintTools.compile_blueprint(blueprint, warnings_as_errors=False)
    if not ASSETS.save_loaded_asset(blueprint, only_if_is_dirty=False):
        fail(f"Could not save {blueprint.get_path_name()}")


def variable_names(blueprint):
    return {str(item) for item in unreal.BlueprintEditorLibrary.list_member_variable_names(blueprint)}


def ensure_variable(blueprint, name, pin_type, editable=True):
    if name not in variable_names(blueprint):
        if not unreal.BlueprintEditorLibrary.add_member_variable(blueprint, name, pin_type):
            fail(f"Could not add variable {name}")
    unreal.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(blueprint, name, editable)


def dispatcher_graph(blueprint, name):
    names = {str(item) for item in unreal.BlueprintEditorLibrary.list_event_dispatchers(blueprint)}
    if name not in names:
        return BlueprintTools.add_event_dispatcher(blueprint, name)
    graph = unreal.BlueprintEditorLibrary.find_graph(blueprint, unreal.Name(name))
    if graph is None:
        fail(f"Dispatcher signature graph unavailable: {name}")
    return graph


def dispatcher_param_names(graph):
    nodes = BlueprintTools.find_nodes(graph)
    if not nodes:
        return set()
    return {
        pin_name(pin)
        for pin in output_pins(nodes[0])
        if pin_name(pin) not in ("then", "OutputDelegate")
    }


def add_dispatcher_object_param(graph, name, object_class):
    if name not in dispatcher_param_names(graph):
        BlueprintTools.add_object_function_param(graph, name, object_class, True)


def add_dispatcher_basic_param(graph, name, type_name):
    if name not in dispatcher_param_names(graph):
        BlueprintTools.add_function_param(graph, name, type_name, True)


def add_dispatcher_enum_param(graph, name, enum_asset):
    if name in dispatcher_param_names(graph):
        return
    blueprint = unreal.Blueprint.cast(graph.get_outer())
    event_graph = unreal.BlueprintEditorLibrary.find_event_graph(blueprint)
    candidates = []
    for query in (enum_asset.get_name(), f"Switch on {enum_asset.get_name()}"):
        for candidate in BlueprintTools.find_node_types(event_graph, query):
            if candidate not in candidates:
                candidates.append(candidate)
    switch_type = next(
        (
            candidate
            for candidate in candidates
            if "switch" in norm(candidate) and norm(enum_asset.get_name()) in norm(candidate)
        ),
        None,
    )
    if switch_type is None:
        fail(f"Could not discover a Switch node for enum {enum_asset.get_name()}; candidates={candidates[:30]}")
    probe = BlueprintTools.create_node(event_graph, switch_type, unreal.IntPoint(-2400, 900))
    try:
        selection = find_pin(probe, "in", ["Selection", enum_asset.get_name()])
        pin_type = unreal.BlueprintGraphPinLibrary.get_pin_type(selection)
    finally:
        unreal.BlueprintGraphEditor.get_graph_editor(event_graph).remove_nodes([probe])
    if not unreal.BlueprintEditorLibrary.add_event_dispatcher_parameter(
        blueprint, unreal.Name(graph.get_name()), unreal.Name(name), pin_type
    ):
        fail(f"Could not add enum dispatcher parameter {name}")


def find_component(blueprint, name):
    cdo = unreal.get_default_object(blueprint.generated_class())
    wanted = norm(name)
    components = ActorTools.get_components(cdo)
    exact = next((item for item in components if item.get_name() == name), None)
    if exact is not None:
        return exact
    # Blueprint template objects may be exposed as Name_GEN_VARIABLE in an
    # unattended editor process even though the SCS display name is Name.
    return next((item for item in components if wanted in norm(item.get_name())), None)


def ensure_components(blueprint):
    compile_and_save(blueprint)
    crate = find_component(blueprint, "CrateMesh")
    if crate is None:
        crate = ActorTools.add_component(blueprint, unreal.SkeletalMeshComponent.static_class(), "CrateMesh")
    if find_component(blueprint, "LootSpawnPoint") is None:
        ActorTools.add_component(blueprint, unreal.SceneComponent.static_class(), "LootSpawnPoint")
    if find_component(blueprint, "CreatureSpawnPoint") is None:
        ActorTools.add_component(blueprint, unreal.SceneComponent.static_class(), "CreatureSpawnPoint")
    compile_and_save(blueprint)

    crate = find_component(blueprint, "CrateMesh")
    loot = find_component(blueprint, "LootSpawnPoint")
    creature = find_component(blueprint, "CreatureSpawnPoint")
    log(f"Components: {[item.get_name() for item in ActorTools.get_components(unreal.get_default_object(blueprint.generated_class()))]}")
    if not all((crate, loot, creature)):
        fail("Could not create the T02 component hierarchy")
    loot.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, 90.0))
    creature.set_editor_property("relative_location", unreal.Vector(120.0, 0.0, -85.0))
    compile_and_save(blueprint)


def ensure_schema(blueprint):
    bool_type = unreal.BlueprintEditorLibrary.get_basic_type_by_name("bool")
    real_type = unreal.BlueprintEditorLibrary.get_basic_type_by_name("real")
    ensure_variable(blueprint, "bOpened", bool_type)
    ensure_variable(blueprint, "bResolved", bool_type)
    ensure_variable(blueprint, "RevealDelay", real_type)
    ensure_variable(blueprint, "bDebugLogging", bool_type)

    opened = dispatcher_graph(blueprint, "OnBoxOpened")
    add_dispatcher_object_param(opened, "Box", unreal.Actor.static_class())

    outcome = dispatcher_graph(blueprint, "OnOutcomeResolved")
    add_dispatcher_enum_param(outcome, "Outcome", load(OUTCOME_PATH))
    add_dispatcher_object_param(outcome, "SpawnedActor", unreal.Actor.static_class())
    add_dispatcher_basic_param(outcome, "bSpawnSucceeded", "bool")

    compile_and_save(blueprint)
    cdo = unreal.get_default_object(blueprint.generated_class())
    cdo.set_editor_property("bOpened", False)
    cdo.set_editor_property("bResolved", False)
    cdo.set_editor_property("RevealDelay", 1.0)
    cdo.set_editor_property("bDebugLogging", True)
    compile_and_save(blueprint)


def clear_t01_t02_event_nodes(event_graph):
    editor = unreal.BlueprintGraphEditor.get_graph_editor(event_graph)
    stale = []
    orphan_event_names = {
        "onmapopenedevent",
        "onmapopened事件",
        "onmediaopenedevent",
        "onmediaopened事件",
        "onboxopenedevent",
        "onboxopened事件",
    }
    for node in editor.list_all_nodes():
        try:
            tag = str(node.get_editor_property("node_comment"))
        except Exception:
            tag = ""
        title = norm(node.get_node_title())
        is_known_orphan = (
            isinstance(node, unreal.K2Node_CustomEvent)
            and title in orphan_event_names
        )
        if (
            tag in ("T01_GENERATED", TAG)
            or ("interact" in title and isinstance(node, unreal.K2Node_Event))
            or is_known_orphan
        ):
            stale.append(node)
    if stale:
        editor.remove_nodes(stale)


def component_getter(event_graph, component_name, x, y):
    return create(
        event_graph,
        [component_name],
        x,
        y,
        include=(norm(component_name),),
        output_words=(component_name,),
    )


def variable_getter(event_graph, name, x, y):
    friendly = name[1:] if name.startswith("b") and len(name) > 1 and name[1].isupper() else name
    wanted = {norm(name), norm(friendly)}
    wanted_tails = {
        norm("Get " + name), norm("Get " + friendly),
        norm("获取" + name), norm("获取" + friendly),
    }
    for search in (name, friendly):
        for candidate in BlueprintTools.find_node_types(event_graph, search):
            # Palette searches for names such as "Opened" also return dispatcher
            # event entries. Reject them before pin introspection, which otherwise
            # creates orphan custom-event nodes as a side effect.
            if norm(str(candidate).split("|")[-1]) not in wanted_tails:
                continue
            try:
                info = BlueprintTools.get_node_type_pins(event_graph, candidate)
            except Exception:
                continue
            inputs = {norm(item.name) for item in info.input_pins}
            outputs = {norm(item.name) for item in info.output_pins}
            if outputs & wanted and "execute" not in inputs:
                return create(event_graph, [candidate], x, y, include=(norm(candidate),))
    fail(f"Could not find exact getter for {name}")


def variable_setter(event_graph, name, x, y):
    friendly = name[1:] if name.startswith("b") and len(name) > 1 and name[1].isupper() else name
    wanted = {norm(name), norm(friendly)}
    wanted_tails = {
        norm("Set " + name), norm("Set " + friendly),
        norm("设置" + name), norm("设置" + friendly),
    }
    for search in (name, friendly):
        for candidate in BlueprintTools.find_node_types(event_graph, search):
            if norm(str(candidate).split("|")[-1]) not in wanted_tails:
                continue
            try:
                info = BlueprintTools.get_node_type_pins(event_graph, candidate)
            except Exception:
                continue
            inputs = {norm(item.name) for item in info.input_pins}
            outputs = {norm(item.name) for item in info.output_pins}
            if inputs & wanted and "execute" in inputs and "then" in outputs:
                return create(event_graph, [candidate], x, y, include=(norm(candidate),))
    fail(f"Could not find exact setter for {name}")


def build_event_graph(blueprint):
    graph = unreal.BlueprintEditorLibrary.find_event_graph(blueprint)
    clear_t01_t02_event_nodes(graph)

    event = create(
        graph,
        ["AddEvent|Interact", "Interact"],
        -1700,
        0,
        include=("interact",),
        exclude=("message", "input", "cast"),
        output_words=("then", "Interactor"),
    )
    valid = create(
        graph, ["Utilities|IsValid", "IsValid"], -1450, 0,
        include=("isvalid",), input_words=("execute",), output_words=("IsValid", "IsNotValid"),
    )
    # Blueprint's localized node palette uses the friendly display name
    # "Opened" for a bool named bOpened (for example, 获取Opened/设置Opened).
    # Match the friendly name and use the pin directions below to distinguish
    # the getter from the setter.
    get_opened = variable_getter(graph, "bOpened", -1450, 250)
    branch = create(
        graph,
        ["分支", "Utilities|FlowControl|Branch", "Branch"],
        -950,
        0,
        include=("流程控制", "分支"),
    )
    set_opened = variable_setter(graph, "bOpened", -700, 0)
    set_default(set_opened, ["bOpened", "Opened", "value"], "true")

    crate = component_getter(graph, "CrateMesh", -700, 350)
    collision = create(
        graph, ["SetCollisionResponseToChannel"], -450, 0,
        include=("setcollisionresponsetochannel",), pin_words=("Channel", "NewResponse"),
    )
    set_default(collision, ["Channel"], "ECC_Visibility")
    set_default(collision, ["NewResponse", "Response"], "ECR_Ignore")

    opened_dispatch = create(graph, ["OnBoxOpened"], -200, 0, include=("callonboxopened",))
    # Object-reference pins accept Blueprint's intrinsic Self literal, which
    # avoids relying on a localized palette entry for "Get a reference to Self".
    set_default(opened_dispatch, ["Box"], "self")
    play_anim = create(graph, ["PlayAnimation"], 50, 0, include=("playanimation",), pin_words=("NewAnimToPlay", "Looping"))
    set_default(play_anim, ["NewAnimToPlay", "Animation"], f"{OPEN_ANIM_PATH}.AS_WoodenCrateOpen")
    set_default(play_anim, ["Looping", "bLooping"], "false")

    actor_location = create(graph, ["GetActorLocation"], 50, 350, include=("getactorlocation",))
    play_sound = create(graph, ["PlaySoundAtLocation"], 350, 0, include=("playsoundatlocation",), pin_words=("Sound", "Location"))
    set_default(play_sound, ["Sound"], f"{OPEN_SOUND_PATH}.SC_WoodenCrateOpen")
    delay = create(graph, ["Utilities|FlowControl|Delay", "Delay", "延迟"], 650, 0, include=("delay",), pin_words=("Duration",))
    get_delay = variable_getter(graph, "RevealDelay", 650, 250)
    printer = create(graph, ["Development|PrintString", "PrintString"], 950, 0, include=("printstring",))
    set_default(printer, ["InString", "String"], "[Box] ResolveOutcome reached")
    set_default(printer, ["PrintToScreen"], "false")
    set_default(printer, ["PrintToLog"], "true")

    connect(event, ["then"], valid, ["execute", "exec"])
    connect(event, ["Interactor"], valid, ["InputObject", "Object"])
    connect(valid, ["IsValid", "Valid"], branch, ["execute", "exec"])
    connect(get_opened, ["bOpened", "Opened", "value"], branch, ["Condition"])
    # Open only from the False path: True means this box was already opened.
    connect(branch, ["False", "else"], set_opened, ["execute", "exec"])
    connect(set_opened, ["then"], collision, ["execute", "exec"])
    connect(crate, ["CrateMesh", "value", "returnvalue"], collision, ["target", "self"])
    connect(collision, ["then"], opened_dispatch, ["execute", "exec"])
    connect(opened_dispatch, ["then"], play_anim, ["execute", "exec"])
    connect(crate, ["CrateMesh", "value", "returnvalue"], play_anim, ["target", "self"])
    connect(play_anim, ["then"], play_sound, ["execute", "exec"])
    connect(actor_location, ["ReturnValue", "Location"], play_sound, ["Location"])
    connect(play_sound, ["then"], delay, ["execute", "exec"])
    connect(get_delay, ["RevealDelay", "value"], delay, ["Duration"])
    connect(delay, ["Completed", "then"], printer, ["execute", "exec"])
    BlueprintTools.arrange_nodes(BlueprintTools.find_nodes(graph))


def main():
    log("Starting official-Python T02 build (no MCP, no PIE)")
    box = load(BOX_PATH)
    load(OPEN_ANIM_PATH)
    load(OPEN_SOUND_PATH)
    ensure_components(box)
    ensure_schema(box)
    build_event_graph(box)
    compile_and_save(box)
    log("BUILD PASS - BP_AnomalyBox compiled and saved; PIE acceptance remains")


if __name__ == "__main__":
    main()
