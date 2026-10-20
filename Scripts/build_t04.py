"""Build T04 money, visual loot, and event-driven HUD assets with Unreal Python.

Run through UnrealEditor/UnrealEditor-Cmd. This script does not start PIE and
does not use the MCP server. It intentionally stops at T04: no spider, spawner,
threat counting, run end, restart, or repeat-loop behavior is created here.
"""

import importlib
import sys
from pathlib import Path

import unreal

from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.actor import ActorTools


PREFIX = "[T04]"
TAG = "T04_GENERATED"
SCRIPT_DIR = str(Path(__file__).resolve().parent)

WALLET_PATH = "/Game/Core/Components/BPC_Wallet"
HIGH_PATH = "/Game/Anomalies/Loot/BP_Loot_HighValue"
TRASH_PATH = "/Game/Anomalies/Loot/BP_Loot_Trash"
HUD_PATH = "/Game/UI/WBP_PrototypeHUD"
CHARACTER_PATH = "/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter"
BOX_PATH = "/Game/Anomalies/Containers/BP_AnomalyBox"
OUTCOME_PATH = "/Game/Core/Types/EAnomalyOutcome"
INTERACTION_PATH = "/Game/Core/Components/BPC_Interaction"
GOLD_MESH_PATH = "/Game/AnimatedWoodenCrateV1/Meshes/SM_WoodenCrateGoldIngots"
CHAIR_MESH_PATH = "/Game/SciFiWorld/Meshes/SM_Chair08"

ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
UMG = unreal.get_default_object(unreal.UMGToolSet)


def log(message):
    unreal.log(f"{PREFIX} {message}")


def fail(message):
    raise RuntimeError(f"{PREFIX} {message}")


def norm(value):
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def load(path):
    asset = ASSETS.load_asset(path)
    if asset is None:
        fail(f"Missing required asset: {path}")
    return asset


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


def create(graph, searches, x, y, include=(), exclude=(), input_words=(), output_words=()):
    return _tag(
        BlueprintTools.create_node(
            graph,
            _node_type(graph, searches, include, exclude, input_words, output_words),
            unreal.IntPoint(x, y),
        )
    )


def _node_type(graph, searches, include=(), exclude=(), input_words=(), output_words=()):
    include = tuple(norm(x) for x in include)
    exclude = tuple(norm(x) for x in exclude)
    input_words = tuple(norm(x) for x in input_words)
    output_words = tuple(norm(x) for x in output_words)
    seen = []
    for search in searches:
        for candidate in BlueprintTools.find_node_types(graph, search):
            if candidate in seen:
                continue
            seen.append(candidate)
            lowered = norm(candidate)
            if include and not all(x in lowered for x in include):
                continue
            if any(x in lowered for x in exclude):
                continue
            try:
                info = BlueprintTools.get_node_type_pins(graph, candidate)
                ins = {norm(x.name) for x in info.input_pins}
                outs = {norm(x.name) for x in info.output_pins}
            except Exception:
                continue
            def pin_matches(word, pin):
                return word == pin if len(word) <= 2 else (word in pin or pin in word)
            if not all(any(pin_matches(x, p) for p in ins) for x in input_words):
                continue
            if not all(any(pin_matches(x, p) for p in outs) for x in output_words):
                continue
            return candidate
    fail(f"No node type matched {searches}; candidates={seen[:60]}")


def _tag(node):
    try:
        node.set_editor_property("node_comment", TAG)
    except Exception:
        pass
    return node


def integer_add_type(graph):
    seen = []
    matches = []
    for search in ("+", "整数", "Integer", "int"):
        for candidate in BlueprintTools.find_node_types(graph, search):
            if candidate in seen:
                continue
            seen.append(candidate)
            try:
                info = BlueprintTools.get_node_type_pins(graph, candidate)
            except Exception:
                continue
            ins = {norm(p.name): norm(p.type_id) for p in info.input_pins}
            outs = {norm(p.name): norm(p.type_id) for p in info.output_pins}
            if not {"a", "b"}.issubset(ins) or "returnvalue" not in outs:
                continue
            matches.append((candidate, ins, outs))
            types = (ins["a"], ins["b"], outs["returnvalue"])
            if all("int" in t or "integer" in t or "整" in t for t in types):
                return candidate
    fail(f"No integer add node found; binary candidates={matches[:40]}")


def textblock_set_text_type(graph, target_get=None):
    seen = []
    matches = []
    context = []
    if target_get is not None:
        target_pin = find_pin(target_get, "out", ["value", target_get.get_node_title()])
        context = [BlueprintTools._pin_to_id(target_pin)]
    for search in ("SetText", "Set Text", "设置文本", "文本"):
        for candidate in BlueprintTools.find_node_types(graph, search, context):
            if candidate in seen:
                continue
            seen.append(candidate)
            try:
                info = BlueprintTools.get_node_type_pins(graph, candidate)
            except Exception:
                continue
            inputs = {norm(p.name): norm(p.type_id) for p in info.input_pins}
            if "intext" not in inputs:
                continue
            target_type = inputs.get("self", inputs.get("target", ""))
            matches.append((candidate, target_type))
            if context:
                return candidate
            if "textblock" in target_type or "文本块" in target_type:
                return candidate
    fail(f"No TextBlock SetText node found; candidates={matches[:40]}")


def textblock_set_text(graph, x, y, target_get=None):
    return _tag(
        BlueprintTools.create_node(graph, textblock_set_text_type(graph, target_get), unreal.IntPoint(x, y))
    )


def context_method_from_pin(graph, target_pin, searches, x, y, input_words=()):
    """Create a member-call node constrained by an explicit target pin type."""
    context = [BlueprintTools._pin_to_id(target_pin)]
    wanted_inputs = tuple(norm(word) for word in input_words)
    seen = []
    diagnostics = []
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    for search in searches:
        for candidate in BlueprintTools.find_node_types(graph, search, context):
            if candidate in seen:
                continue
            seen.append(candidate)
            try:
                info = BlueprintTools.get_node_type_pins(graph, candidate)
            except Exception:
                continue
            inputs = {norm(pin.name) for pin in info.input_pins}
            if not all(any(word in pin or pin in word for pin in inputs) for word in wanted_inputs):
                continue
            node = editor.create_node_from_name(
                candidate, unreal.Vector2D(float(x), float(y)), [target_pin]
            )
            if node is None:
                diagnostics.append((candidate, "context creation returned None"))
                continue
            _tag(node)
            target = find_pin(node, "in", ["target", "self"], required=False)
            already_connected = target and target_pin in list(target.list_connected_pins())
            if target and (already_connected or target_pin.try_create_connection(target)):
                return node
            diagnostics.append(
                (
                    candidate,
                    BlueprintTools._pin_to_id(target_pin),
                    BlueprintTools._pin_to_id(target) if target else None,
                    [(pin.name, pin.type_id) for pin in info.input_pins],
                )
            )
            editor.remove_nodes([node])
    fail(
        f"No context-compatible widget method matched {searches}; "
        f"candidates={seen[:60]}; diagnostics={diagnostics[:20]}"
    )


def context_method_node(graph, target_get, searches, x, y, input_words=()):
    """Create a member-call node constrained by the target object's pin type."""
    target_pin = find_pin(target_get, "out", ["value", target_get.get_node_title()])
    return context_method_from_pin(graph, target_pin, searches, x, y, input_words)


def context_node_from_pin(graph, source_pin, searches, x, y, input_aliases, output_aliases):
    """Create a generic node using a data pin as the action-menu context."""
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    context = [BlueprintTools._pin_to_id(source_pin)]
    seen = []
    for search in searches:
        for candidate in BlueprintTools.find_node_types(graph, search, context):
            if candidate in seen:
                continue
            seen.append(candidate)
            node = editor.create_node_from_name(
                candidate, unreal.Vector2D(float(x), float(y)), [source_pin]
            )
            if node is None:
                continue
            _tag(node)
            if (
                find_pin(node, "in", input_aliases, required=False) is not None
                and find_pin(node, "out", output_aliases, required=False) is not None
            ):
                return node
            editor.remove_nodes([node])
    fail(f"No context node matched {searches}; candidates={seen[:100]}")


def compile_and_save(blueprint, widget=False):
    if widget:
        if not UMG.call_method("CompileWidgetBlueprint", (blueprint,)):
            fail(f"Widget compile failed: {blueprint.get_path_name()}")
    else:
        BlueprintTools.compile_blueprint(blueprint, warnings_as_errors=False)
        graph = unreal.BlueprintEditorLibrary.find_event_graph(blueprint)
        if graph:
            errors = unreal.BlueprintGraphEditor.get_graph_editor(graph).list_nodes_with_errors()
            if errors:
                fail(f"Compile errors in {blueprint.get_name()}: {[str(n.get_node_title()) for n in errors]}")
    if not ASSETS.save_loaded_asset(blueprint, only_if_is_dirty=False):
        fail(f"Could not save {blueprint.get_path_name()}")


def ensure_blueprint(path, parent_class):
    asset = ASSETS.load_asset(path)
    if asset:
        return asset
    folder, name = path.rsplit("/", 1)
    return BlueprintTools.create(folder, name, parent_class)


def member_names(blueprint):
    return {str(x) for x in unreal.BlueprintEditorLibrary.list_member_variable_names(blueprint, False)}


def ensure_variable(blueprint, name, pin_type, editable=False):
    if name not in member_names(blueprint):
        if not unreal.BlueprintEditorLibrary.add_member_variable(blueprint, name, pin_type):
            fail(f"Could not add variable {name} to {blueprint.get_name()}")
    unreal.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(blueprint, name, editable)


def variable_getter(graph, name, x, y):
    friendly = name[1:] if name.startswith("b") and len(name) > 1 and name[1].isupper() else name
    tails = {norm("Get " + name), norm("Get " + friendly), norm("获取" + name), norm("获取" + friendly)}
    wanted = {norm(name), norm(friendly)}
    searches = dict.fromkeys(
        (name, friendly, name.replace("_", ""), name.replace("_", " "),
         friendly.replace("_", ""), friendly.replace("_", " "))
    )
    for search in searches:
        for candidate in BlueprintTools.find_node_types(graph, search):
            if norm(str(candidate).split("|")[-1]) not in tails:
                continue
            try:
                info = BlueprintTools.get_node_type_pins(graph, candidate)
            except Exception:
                continue
            ins = {norm(p.name) for p in info.input_pins}
            outs = {norm(p.name) for p in info.output_pins}
            if outs & wanted and "execute" not in ins:
                return _tag(BlueprintTools.create_node(graph, candidate, unreal.IntPoint(x, y)))
    fail(f"Could not find getter for {name} in {graph.get_name()}")


def variable_setter(graph, name, x, y):
    friendly = name[1:] if name.startswith("b") and len(name) > 1 and name[1].isupper() else name
    tails = {norm("Set " + name), norm("Set " + friendly), norm("设置" + name), norm("设置" + friendly)}
    wanted = {norm(name), norm(friendly)}
    searches = dict.fromkeys(
        (name, friendly, name.replace("_", ""), name.replace("_", " "),
         friendly.replace("_", ""), friendly.replace("_", " "))
    )
    for search in searches:
        for candidate in BlueprintTools.find_node_types(graph, search):
            if norm(str(candidate).split("|")[-1]) not in tails:
                continue
            try:
                info = BlueprintTools.get_node_type_pins(graph, candidate)
            except Exception:
                continue
            ins = {norm(p.name) for p in info.input_pins}
            outs = {norm(p.name) for p in info.output_pins}
            if ins & wanted and "execute" in ins and "then" in outs:
                return _tag(BlueprintTools.create_node(graph, candidate, unreal.IntPoint(x, y)))
    fail(f"Could not find setter for {name} in {graph.get_name()}")


def component_getter(graph, name, x, y):
    return variable_getter(graph, name, x, y)


def rebuild_function(blueprint, name):
    existing = next((g for g in BlueprintTools.list_graphs(blueprint) if g.get_name() == name), None)
    if existing:
        BlueprintTools.remove_function_graph(blueprint, name)
    return BlueprintTools.add_function_graph(blueprint, name)


def entry_node(graph):
    nodes = BlueprintTools.find_nodes(graph)
    entry = next((n for n in nodes if isinstance(n, unreal.K2Node_FunctionEntry)), None)
    if entry is None:
        fail(f"No function entry in {graph.get_name()}")
    return entry


def result_node(graph):
    nodes = BlueprintTools.find_nodes(graph)
    return next((n for n in nodes if isinstance(n, unreal.K2Node_FunctionResult)), None)


def add_basic_param(graph, name, type_name, is_input):
    BlueprintTools.add_function_param(graph, name, type_name, is_input)


def add_object_param(graph, name, cls, is_input):
    BlueprintTools.add_object_function_param(graph, name, cls, is_input)


def enum_pin_type(enum_asset):
    box = load(BOX_PATH)
    graph = unreal.BlueprintEditorLibrary.find_event_graph(box)
    switch_type = _node_type(graph, [enum_asset.get_name()], include=("switch", enum_asset.get_name()))
    probe = BlueprintTools.create_node(graph, switch_type, unreal.IntPoint(-3000, 1000))
    try:
        return unreal.BlueprintGraphPinLibrary.get_pin_type(find_pin(probe, "in", ["Selection"]))
    finally:
        unreal.BlueprintGraphEditor.get_graph_editor(graph).remove_nodes([probe])


def add_enum_param(graph, blueprint, name, pin_type, is_input):
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    if is_input:
        editor.add_graph_input_parameter(name, pin_type)
    else:
        editor.add_graph_output_parameter(name, pin_type)


def ensure_dispatcher(blueprint, name, params):
    names = {str(x) for x in unreal.BlueprintEditorLibrary.list_event_dispatchers(blueprint)}
    if name in names:
        BlueprintTools.remove_function_graph(blueprint, name)
    graph = BlueprintTools.add_event_dispatcher(blueprint, name)
    for kind, param_name, value in params:
        if kind == "basic":
            BlueprintTools.add_function_param(graph, param_name, value, True)
        elif kind == "object":
            BlueprintTools.add_object_function_param(graph, param_name, value, True)
        elif kind == "enum":
            if not unreal.BlueprintEditorLibrary.add_event_dispatcher_parameter(
                blueprint, unreal.Name(name), unreal.Name(param_name), value
            ):
                fail(f"Could not add enum dispatcher parameter {param_name}")


def build_wallet():
    wallet = ensure_blueprint(WALLET_PATH, unreal.ActorComponent.static_class())
    int_type = unreal.BlueprintEditorLibrary.get_basic_type_by_name("int")
    bool_type = unreal.BlueprintEditorLibrary.get_basic_type_by_name("bool")
    ensure_variable(wallet, "Money", int_type, False)
    ensure_variable(wallet, "bDebugLogging", bool_type, True)
    ensure_dispatcher(wallet, "OnMoneyChanged", (
        ("basic", "NewMoney", "int"), ("basic", "Delta", "int")
    ))
    compile_and_save(wallet)

    add = rebuild_function(wallet, "AddMoney")
    add_basic_param(add, "Amount", "int", True)
    entry = entry_node(add)
    get_money = variable_getter(add, "Money", -650, 180)
    plus = _tag(BlueprintTools.create_node(add, integer_add_type(add), unreal.IntPoint(-400, 180)))
    set_money = variable_setter(add, "Money", -100, 0)
    connect(get_money, ["Money", "value"], plus, ["A"])
    connect(entry, ["Amount"], plus, ["B"])
    connect(entry, ["then"], set_money, ["execute", "exec"])
    connect(plus, ["ReturnValue"], set_money, ["Money", "value"])

    formatter = create(add, ["FormatText", "Format Text", "格式化文本"], 250, 180)
    set_default(formatter, ["Format"], "[Wallet] Delta={Delta} NewMoney={NewMoney}")
    connect(entry, ["Amount"], formatter, ["Delta"])
    connect(plus, ["ReturnValue"], formatter, ["NewMoney"])
    printer = create(add, ["PrintString"], 650, 0, include=("printstring",))
    set_default(printer, ["PrintToScreen"], "false")
    set_default(printer, ["PrintToLog"], "true")
    connect(set_money, ["then"], printer, ["execute", "exec"])
    connect(formatter, ["Result", "ReturnValue"], printer, ["InString", "String"])
    dispatch = _tag(BlueprintTools.create_node(add, "默认|CallOnMoneyChanged", unreal.IntPoint(900, 0)))
    connect(printer, ["then"], dispatch, ["execute", "exec"])
    connect(plus, ["ReturnValue"], dispatch, ["NewMoney"])
    connect(entry, ["Amount"], dispatch, ["Delta"])

    get_graph = rebuild_function(wallet, "GetMoney")
    add_basic_param(get_graph, "MoneyValue", "int", False)
    get_var = variable_getter(get_graph, "Money", -200, 100)
    connect(get_var, ["Money", "value"], result_node(get_graph), ["MoneyValue"])

    reset = rebuild_function(wallet, "ResetMoney")
    reset_entry = entry_node(reset)
    reset_set = variable_setter(reset, "Money", -100, 0)
    set_default(reset_set, ["Money", "value"], "0")
    reset_dispatch = _tag(BlueprintTools.create_node(reset, "默认|CallOnMoneyChanged", unreal.IntPoint(200, 0)))
    set_default(reset_dispatch, ["NewMoney"], "0")
    set_default(reset_dispatch, ["Delta"], "0")
    connect(reset_entry, ["then"], reset_set, ["execute", "exec"])
    connect(reset_set, ["then"], reset_dispatch, ["execute", "exec"])

    compile_and_save(wallet)
    cdo = unreal.get_default_object(wallet.generated_class())
    cdo.set_editor_property("Money", 0)
    cdo.set_editor_property("bDebugLogging", True)
    compile_and_save(wallet)
    log("Built BPC_Wallet")
    return wallet


def build_loot(path, mesh_path, scale, rotation):
    blueprint = ensure_blueprint(path, unreal.Actor.static_class())
    compile_and_save(blueprint)
    cdo = unreal.get_default_object(blueprint.generated_class())
    mesh_component = next(
        (c for c in ActorTools.get_components(cdo) if isinstance(c, unreal.StaticMeshComponent)), None
    )
    if mesh_component is None or "LootVisual" not in mesh_component.get_name():
        mesh_component = ActorTools.add_component(
            blueprint, unreal.StaticMeshComponent.static_class(), "LootVisual"
        )
    compile_and_save(blueprint)
    mesh_component = next(
        (
            c for c in ActorTools.get_components(unreal.get_default_object(blueprint.generated_class()))
            if isinstance(c, unreal.StaticMeshComponent) and "lootvisual" in norm(c.get_name())
        ),
        None,
    )
    if mesh_component is None:
        fail(f"LootVisual component missing after compile in {blueprint.get_name()}")
    mesh_component.set_static_mesh(load(mesh_path))
    mesh_component.set_simulate_physics(False)
    mesh_component.set_editor_property("generate_overlap_events", False)
    mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    mesh_component.set_editor_property("relative_scale3d", unreal.Vector(*scale))
    mesh_component.set_editor_property("relative_rotation", unreal.Rotator(*rotation))
    compile_and_save(blueprint)
    log(f"Built {blueprint.get_name()} with {mesh_path}")
    return blueprint


def slate_color(r, g, b, a=1.0):
    return unreal.SlateColor(specified_color=unreal.LinearColor(r, g, b, a))


def set_canvas_slot(slot, anchors, position, size, alignment=(0.0, 0.0)):
    slot.set_anchors(
        unreal.Anchors(
            minimum=unreal.Vector2D(anchors[0], anchors[1]),
            maximum=unreal.Vector2D(anchors[2], anchors[3]),
        )
    )
    slot.set_position(unreal.Vector2D(*position))
    slot.set_size(unreal.Vector2D(*size))
    slot.set_alignment(unreal.Vector2D(*alignment))


def umg_add(hud, cls, name, parent=None):
    result = UMG.call_method("AddWidget", (hud, cls, name, parent, -1))
    if result.widget is None:
        fail(f"Could not add HUD widget {name}")
    return result


def build_hud_tree(hud):
    tree = UMG.call_method("GetWidgets", (hud,))
    if tree.widgets:
        root = tree.widgets[0].widget
        if not UMG.call_method("RemoveWidget", (hud, root)):
            fail("Could not clear existing HUD widget tree")

    root = umg_add(hud, unreal.CanvasPanel.static_class(), "RootCanvas").widget
    money = umg_add(hud, unreal.TextBlock.static_class(), "MoneyText", root)
    money.widget.set_text(unreal.Text("Money: $0"))
    money.widget.set_font_size(26)
    money.widget.set_color_and_opacity(slate_color(1.0, 1.0, 1.0))
    set_canvas_slot(money.slot, (0.0, 0.0, 0.0, 0.0), (32.0, 28.0), (420.0, 42.0))

    threats = umg_add(hud, unreal.TextBlock.static_class(), "ThreatText", root)
    threats.widget.set_text(unreal.Text("Threats: 0 / 2"))
    threats.widget.set_font_size(22)
    threats.widget.set_color_and_opacity(slate_color(0.85, 0.9, 1.0))
    set_canvas_slot(threats.slot, (0.0, 0.0, 0.0, 0.0), (32.0, 72.0), (360.0, 36.0))

    crosshair = umg_add(hud, unreal.TextBlock.static_class(), "CrosshairText", root)
    crosshair.widget.set_text(unreal.Text("+"))
    crosshair.widget.set_font_size(28)
    crosshair.widget.set_editor_property("justification", unreal.TextJustify.CENTER)
    crosshair.widget.set_color_and_opacity(slate_color(1.0, 1.0, 1.0))
    set_canvas_slot(crosshair.slot, (0.5, 0.5, 0.5, 0.5), (0.0, 0.0), (40.0, 40.0), (0.5, 0.5))

    prompt = umg_add(hud, unreal.TextBlock.static_class(), "InteractionPrompt", root)
    prompt.widget.set_text(unreal.Text("[E] OPEN"))
    prompt.widget.set_font_size(22)
    prompt.widget.set_editor_property("justification", unreal.TextJustify.CENTER)
    prompt.widget.set_color_and_opacity(slate_color(1.0, 1.0, 1.0))
    prompt.widget.set_visibility(unreal.SlateVisibility.COLLAPSED)
    set_canvas_slot(prompt.slot, (0.5, 0.5, 0.5, 0.5), (0.0, 48.0), (260.0, 40.0), (0.5, 0.5))

    result = umg_add(hud, unreal.TextBlock.static_class(), "ResultText", root)
    result.widget.set_text(unreal.Text("HIGH VALUE +$5,000"))
    result.widget.set_font_size(38)
    result.widget.set_editor_property("justification", unreal.TextJustify.CENTER)
    result.widget.set_color_and_opacity(slate_color(1.0, 0.72, 0.08))
    result.widget.set_visibility(unreal.SlateVisibility.COLLAPSED)
    result.widget.set_render_opacity(0.0)
    set_canvas_slot(result.slot, (0.5, 0.5, 0.5, 0.5), (0.0, -92.0), (720.0, 70.0), (0.5, 0.5))

    for info in (money, threats, crosshair, prompt, result):
        UMG.call_method("ToggleWidgetAsVariable", (hud, info.widget, True))
    compile_and_save(hud, widget=True)


def hud_widget_getter(graph, name, x, y):
    return variable_getter(graph, name, x, y)


def reset_hud_graphs(hud):
    """Remove incomplete T04 graphs before compiling the rebuilt widget tree."""
    for name in ("UpdateMoney", "UpdateFocus", "ShowOutcome"):
        if any(graph.get_name() == name for graph in BlueprintTools.list_graphs(hud)):
            BlueprintTools.remove_function_graph(hud, name)
    event_graph = unreal.BlueprintEditorLibrary.find_event_graph(hud)
    if event_graph:
        editor = unreal.BlueprintGraphEditor.get_graph_editor(event_graph)
        stale = []
        for node in list(editor.list_all_nodes()):
            try:
                if str(node.get_editor_property("node_comment")) == TAG:
                    stale.append(node)
            except Exception:
                pass
        if stale:
            editor.remove_nodes(stale)


def set_visibility_node(graph, widget_get, visibility, x, y):
    node = context_method_node(
        graph, widget_get, ["SetVisibility", "设置可见性"], x, y,
        input_words=("InVisibility",),
    )
    set_default(node, ["InVisibility", "Visibility"], visibility)
    return node


def build_hud_graphs(hud, outcome_enum, outcome_type):
    update_money = rebuild_function(hud, "UpdateMoney")
    add_basic_param(update_money, "NewMoney", "int", True)
    compile_and_save(hud, widget=True)
    entry = entry_node(update_money)
    to_text = create(
        update_money, ["ToText (Integer)", "Conv_IntToText", "整数转文本", "文本", "Text", "整数"], -500, 180,
        input_words=("Value", "UseGrouping"), output_words=("ReturnValue",),
    )
    set_default(to_text, ["UseGrouping", "Grouping"], "true")
    set_default(to_text, ["MinimumIntegralDigits"], "1")
    connect(entry, ["NewMoney"], to_text, ["Value"])
    formatter = create(update_money, ["FormatText", "Format Text", "格式化文本"], -250, 180)
    set_default(formatter, ["Format"], "Money: ${Money}")
    connect(to_text, ["ReturnValue"], formatter, ["Money"])
    money_get = hud_widget_getter(update_money, "MoneyText", -250, 380)
    set_text = textblock_set_text(update_money, 50, 0, money_get)
    connect(entry, ["then"], set_text, ["execute", "exec"])
    connect(money_get, ["MoneyText", "value"], set_text, ["target", "self"])
    connect(formatter, ["Result", "ReturnValue"], set_text, ["InText", "Text"])

    update_focus = rebuild_function(hud, "UpdateFocus")
    add_object_param(update_focus, "FocusedActor", unreal.Actor.static_class(), True)
    compile_and_save(hud, widget=True)
    entry = entry_node(update_focus)
    valid = create(
        update_focus, ["IsValid"], -450, 180,
        include=("isvalid",), exclude=("soft",), input_words=("InputObject",), output_words=("ReturnValue",),
    )
    connect(entry, ["FocusedActor"], valid, ["InputObject", "Object"])
    branch = create(
        update_focus, ["工具|流程控制|分支", "Branch", "分支"], -150, 0,
        include=("流程控制", "分支"),
    )
    connect(entry, ["then"], branch, ["execute", "exec"])
    connect(valid, ["ReturnValue"], branch, ["Condition"])
    prompt_a = hud_widget_getter(update_focus, "InteractionPrompt", -100, 250)
    show = set_visibility_node(update_focus, prompt_a, "Visible", 150, -50)
    prompt_b = hud_widget_getter(update_focus, "InteractionPrompt", -100, 450)
    hide = set_visibility_node(update_focus, prompt_b, "Collapsed", 150, 150)
    connect(branch, ["True", "then"], show, ["execute", "exec"])
    connect(branch, ["False", "else"], hide, ["execute", "exec"])

    # Register the custom event before looking up call nodes for it in
    # ShowOutcome.  The animation body is populated after that function.
    event_graph = unreal.BlueprintEditorLibrary.find_event_graph(hud)
    animate = BlueprintTools.add_event(hud, "AnimateResult", unreal.IntPoint(-1100, 0))
    _tag(animate)
    compile_and_save(hud, widget=True)

    show_outcome = rebuild_function(hud, "ShowOutcome")
    add_enum_param(show_outcome, hud, "Outcome", outcome_type, True)
    compile_and_save(hud, widget=True)
    entry = entry_node(show_outcome)
    switch_type = _node_type(show_outcome, [outcome_enum.get_name()], include=("switch", outcome_enum.get_name()))
    switch = _tag(BlueprintTools.create_node(show_outcome, switch_type, unreal.IntPoint(-450, 0)))
    connect(entry, ["then"], switch, ["execute", "exec"])
    connect(entry, ["Outcome"], switch, ["Selection"])
    outcome_specs = (
        ("NewEnumerator0", "HIGH VALUE +$5,000", -250),
        ("NewEnumerator1", "TRASH +$3", 50),
        ("NewEnumerator2", "WARNING", 350),
    )
    for enum_pin, message, y in outcome_specs:
        widget_get = hud_widget_getter(show_outcome, "ResultText", -150, y + 180)
        text_node = textblock_set_text(show_outcome, -50, y, widget_get)
        set_default(text_node, ["InText", "Text"], message)
        connect(widget_get, ["ResultText", "value"], text_node, ["target", "self"])
        animate_call = create(show_outcome, ["AnimateResult"], 250, y, include=("animateresult",))
        connect(switch, [enum_pin], text_node, ["execute", "exec"])
        connect(text_node, ["then"], animate_call, ["execute", "exec"])

    editor = unreal.BlueprintGraphEditor.get_graph_editor(event_graph)
    result_get = hud_widget_getter(event_graph, "ResultText", -1100, 300)
    show = set_visibility_node(event_graph, result_get, "Visible", -850, 0)
    connect(animate, ["then"], show, ["execute", "exec"])

    previous = show
    opacities = ((0.0, 0.05), (0.33, 0.05), (0.67, 0.05), (1.0, 1.35),
                 (0.8, 0.05), (0.6, 0.05), (0.4, 0.05), (0.2, 0.05), (0.0, None))
    x = -600
    for opacity, delay_value in opacities:
        opacity_node = context_method_node(
            event_graph, result_get, ["SetRenderOpacity", "设置渲染不透明度"], x, 0,
            input_words=("InOpacity",),
        )
        set_default(opacity_node, ["InOpacity", "Opacity"], str(opacity))
        connect(previous, ["then", "Completed"], opacity_node, ["execute", "exec"])
        previous = opacity_node
        x += 230
        if delay_value is not None:
            delay = create(event_graph, ["Delay", "延迟"], x, 0, include=("delay",), input_words=("Duration",))
            set_default(delay, ["Duration"], str(delay_value))
            connect(previous, ["then"], delay, ["execute", "exec"])
            previous = delay
            x += 230
    result_get_end = hud_widget_getter(event_graph, "ResultText", x, 260)
    collapse = set_visibility_node(event_graph, result_get_end, "Collapsed", x, 0)
    connect(previous, ["then", "Completed"], collapse, ["execute", "exec"])

    BlueprintTools.arrange_nodes(BlueprintTools.find_nodes(event_graph))
    compile_and_save(hud, widget=True)
    log("Built WBP_PrototypeHUD tree and event-driven update graphs")


def build_hud(outcome_enum, outcome_type):
    hud = ASSETS.load_asset(HUD_PATH)
    if hud is None:
        hud = UMG.call_method(
            "CreateWidgetBlueprint", ("/Game/UI", "WBP_PrototypeHUD", unreal.UserWidget.static_class())
        )
    if hud is None:
        fail("Could not create WBP_PrototypeHUD")
    reset_hud_graphs(hud)
    build_hud_tree(hud)
    build_hud_graphs(hud, outcome_enum, outcome_type)
    return hud


def insert_opening_interactor(box):
    graph = unreal.BlueprintEditorLibrary.find_event_graph(box)
    event = next(
        (
            n for n in BlueprintTools.find_nodes(graph)
            if isinstance(n, unreal.K2Node_Event)
            and find_pin(n, "out", ["Interactor"], required=False) is not None
        ),
        None,
    )
    set_opened = next(
        (
            n for n in BlueprintTools.find_nodes(graph)
            if "variableset" in norm(n.get_class().get_name())
            and find_pin(n, "in", ["bOpened", "Opened"], required=False) is not None
        ),
        None,
    )
    if event is None or set_opened is None:
        fail("Could not locate accepted T03 Interact/set bOpened nodes")
    then_pin = find_pin(set_opened, "out", ["then"])
    downstream = list(then_pin.list_connected_pins())
    for pin in downstream:
        then_pin.break_single_pin_link(pin)
    setter = variable_setter(graph, "OpeningInteractor", -300, 50)
    connect(set_opened, ["then"], setter, ["execute", "exec"])
    connect(event, ["Interactor"], setter, ["OpeningInteractor", "value"])
    for pin in downstream:
        if not find_pin(setter, "out", ["then"]).try_create_connection(pin):
            fail("Could not restore box opening execution after caching Interactor")


def pure_is_valid(graph, x, y):
    return create(
        graph, ["IsValid"], x, y,
        include=("isvalid",), exclude=("soft",), input_words=("InputObject",), output_words=("ReturnValue",),
    )


def dynamic_cast_to(graph, target_class, x, y):
    """Create a stock Actor cast and retarget its baked class to target_class."""
    type_id = None
    seen = []
    for search in ("Cast To Actor", "转换为Actor", "Actor"):
        for candidate in BlueprintTools.find_node_types(graph, search):
            if candidate in seen:
                continue
            seen.append(candidate)
            try:
                info = BlueprintTools.get_node_type_pins(graph, candidate)
            except Exception:
                continue
            inputs = {norm(pin.name) for pin in info.input_pins}
            outputs = {norm(pin.name) for pin in info.output_pins}
            if "object" in inputs and ("asactor" in outputs or "actor" in outputs):
                type_id = candidate
                break
        if type_id:
            break
    if type_id is None:
        fail(f"Could not find exact stock Cast To Actor; candidates={seen[:100]}")
    node = _tag(BlueprintTools.create_node(graph, type_id, unreal.IntPoint(x, y)))
    BlueprintTools.retarget_node_class(node, unreal.Actor.static_class(), target_class)
    return node


def box_final(graph, x, y, spawned, succeeded, outcome_name):
    resolved = variable_setter(graph, "bResolved", x, y)
    set_default(resolved, ["bResolved", "Resolved", "value"], "true")
    dispatch = _tag(BlueprintTools.create_node(graph, "默认|CallOnOutcomeResolved", unreal.IntPoint(x + 260, y)))
    set_default(dispatch, ["Outcome"], outcome_name)
    if spawned is not None:
        connect(spawned, ["ReturnValue"], dispatch, ["SpawnedActor"])
    if succeeded is not None:
        connect(succeeded, ["ReturnValue"], dispatch, ["bSpawnSucceeded", "SpawnSucceeded"])
    else:
        set_default(dispatch, ["bSpawnSucceeded", "SpawnSucceeded"], "false")
    connect(resolved, ["then"], dispatch, ["execute", "exec"])
    return resolved


def reward_tail(graph, source_pin, x, y, display, outcome_name, class_var, amount_var, wallet):
    spawn_point = component_getter(graph, "LootSpawnPoint", x, y + 420)
    world_transform = create(
        graph, ["GetWorldTransform"], x + 200, y + 420,
        include=("getworldtransform",), output_words=("ReturnValue",),
    )
    connect(spawn_point, ["LootSpawnPoint", "value"], world_transform, ["target", "self"])
    class_get = variable_getter(graph, class_var, x, y + 650)
    spawn = create(
        graph,
        ["SpawnActorFromClass", "Spawn Actor from Class", "从类生成Actor", "生成Actor", "Actor"],
        x + 400,
        y,
        input_words=("Class", "SpawnTransform"),
        output_words=("ReturnValue",),
    )
    connect(class_get, [class_var, "value"], spawn, ["Class"])
    connect(world_transform, ["ReturnValue"], spawn, ["SpawnTransform"])
    find_pin(spawn, "in", ["execute", "exec"]).try_create_connection(source_pin)
    valid = pure_is_valid(graph, x + 650, y + 420)
    connect(spawn, ["ReturnValue"], valid, ["InputObject", "Object"])

    sequence = create(
        graph, ["工具|流程控制|序列", "Sequence", "序列"], x + 650, y,
        include=("流程控制", "序列"),
    )
    connect(spawn, ["then"], sequence, ["execute", "exec"])
    check = create(
        graph, ["工具|流程控制|分支", "Branch", "分支"], x + 900, y - 120,
        include=("流程控制", "分支"),
    )
    connect(sequence, ["then0"], check, ["execute", "exec"])
    connect(valid, ["ReturnValue"], check, ["Condition"])
    error = create(graph, ["PrintString"], x + 1150, y - 120, include=("printstring",))
    set_default(error, ["InString", "String"], f"[Box] ERROR {display} visual spawn failed")
    set_default(error, ["PrintToLog"], "true")
    set_default(error, ["PrintToScreen"], "true")
    connect(check, ["False", "else"], error, ["execute", "exec"])

    result_log = create(graph, ["PrintString"], x + 900, y + 100, include=("printstring",))
    set_default(result_log, ["InString", "String"], f"[Box] Outcome={display}")
    set_default(result_log, ["PrintToLog"], "true")
    set_default(result_log, ["PrintToScreen"], "false")
    connect(sequence, ["then1"], result_log, ["execute", "exec"])

    interactor = variable_getter(graph, "OpeningInteractor", x + 900, y + 600)
    get_component = create(
        graph, ["GetComponentByClass", "Get Component by Class"], x + 1150, y + 500,
        include=("getcomponentbyclass",), input_words=("ComponentClass",), output_words=("ReturnValue",),
    )
    set_default(get_component, ["ComponentClass"], wallet.generated_class().get_path_name())
    connect(interactor, ["OpeningInteractor", "value"], get_component, ["target", "self"])
    cast_wallet = dynamic_cast_to(graph, wallet.generated_class(), x + 1400, y + 100)
    connect(get_component, ["ReturnValue"], cast_wallet, ["Object"])
    wallet_pin = find_pin(cast_wallet, "out", ["As BPC_Wallet", "BPC_Wallet"])
    add_money = context_method_from_pin(
        graph, wallet_pin, ["AddMoney"], x + 1650, y + 100
    )
    amount = variable_getter(graph, amount_var, x + 1200, y + 700)
    connect(result_log, ["then"], cast_wallet, ["execute", "exec"])
    connect(cast_wallet, ["then"], add_money, ["execute", "exec"])
    connect(amount, [amount_var, "value"], add_money, ["Amount"])
    final = box_final(graph, x + 1900, y + 100, spawn, valid, outcome_name)
    connect(add_money, ["then"], final, ["execute", "exec"])


def threat_tail(graph, source_pin, x, y, display, outcome_name):
    printer = create(graph, ["PrintString"], x, y, include=("printstring",))
    set_default(printer, ["InString", "String"], f"[Box] Outcome={display}")
    set_default(printer, ["PrintToLog"], "true")
    set_default(printer, ["PrintToScreen"], "false")
    find_pin(printer, "in", ["execute", "exec"]).try_create_connection(source_pin)
    final = box_final(graph, x + 260, y, None, None, outcome_name)
    connect(printer, ["then"], final, ["execute", "exec"])


def replace_t03_outcome_tails(box, wallet):
    graph = unreal.BlueprintEditorLibrary.find_event_graph(box)
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    tails = []
    for node in list(editor.list_all_nodes()):
        if "printstring" not in norm(BlueprintTools._get_node_info(node).type_id):
            continue
        pin = find_pin(node, "in", ["InString", "String"], required=False)
        if pin is None:
            continue
        value = str(pin.get_pin_value())
        if value.startswith("[Box] Forced Outcome=") or value.startswith("[Box] Roll="):
            exec_in = find_pin(node, "in", ["execute", "exec"])
            sources = list(exec_in.list_connected_pins())
            if len(sources) != 1:
                fail(f"Expected one switch source for {value}")
            then = find_pin(node, "out", ["then"])
            setters = [p.get_owning_node() for p in then.list_connected_pins()]
            remove = [node]
            for setter in setters:
                remove.append(setter)
                setter_then = find_pin(setter, "out", ["then"], required=False)
                if setter_then:
                    remove.extend(p.get_owning_node() for p in setter_then.list_connected_pins())
            tails.append((value, sources[0], remove))
    if len(tails) != 6:
        fail(f"Expected six T03 outcome tails, found {len(tails)}")
    removed = []
    for _, _, nodes in tails:
        for node in nodes:
            if node not in removed:
                removed.append(node)
    editor.remove_nodes(removed)

    for index, (label, source_pin, _) in enumerate(tails):
        display = label.split("=")[-1]
        x = 2900 if "Forced" in label else 3000
        y = -800 + index * 330
        internal = {"HighValue": "NewEnumerator0", "Trash": "NewEnumerator1", "Threat": "NewEnumerator2"}[display]
        if display == "HighValue":
            reward_tail(graph, source_pin, x, y, display, internal, "HighValueClass", "HighValueAmount", wallet)
        elif display == "Trash":
            reward_tail(graph, source_pin, x, y, display, internal, "TrashClass", "TrashAmount", wallet)
        else:
            threat_tail(graph, source_pin, x, y, display, internal)
    BlueprintTools.arrange_nodes(BlueprintTools.find_nodes(graph))


def build_box(wallet, high, trash):
    box = load(BOX_PATH)
    int_type = unreal.BlueprintEditorLibrary.get_basic_type_by_name("int")
    actor_type = unreal.BlueprintEditorLibrary.get_object_reference_type(unreal.Actor.static_class())
    class_type = unreal.BlueprintEditorLibrary.get_class_reference_type(unreal.Actor.static_class())
    ensure_variable(box, "OpeningInteractor", actor_type, False)
    ensure_variable(box, "HighValueAmount", int_type, True)
    ensure_variable(box, "TrashAmount", int_type, True)
    ensure_variable(box, "HighValueClass", class_type, True)
    ensure_variable(box, "TrashClass", class_type, True)
    compile_and_save(box)

    if SCRIPT_DIR not in sys.path:
        sys.path.insert(0, SCRIPT_DIR)
    # build_t03 currently invokes main() at module import, so import it once.
    import build_t03  # noqa: F401
    box = load(BOX_PATH)
    insert_opening_interactor(box)
    replace_t03_outcome_tails(box, wallet)
    compile_and_save(box)
    cdo = unreal.get_default_object(box.generated_class())
    cdo.set_editor_property("HighValueAmount", 5000)
    cdo.set_editor_property("TrashAmount", 3)
    cdo.set_editor_property("HighValueClass", high.generated_class())
    cdo.set_editor_property("TrashClass", trash.generated_class())
    compile_and_save(box)
    log("Modified BP_AnomalyBox for visual spawning and wallet payment")
    return box


def build_handler(character, name, params, hud_function):
    graph = rebuild_function(character, name)
    for kind, param_name, value in params:
        if kind == "basic":
            add_basic_param(graph, param_name, value, True)
        elif kind == "object":
            add_object_param(graph, param_name, value, True)
        elif kind == "enum":
            add_enum_param(graph, character, param_name, value, True)
    compile_and_save(character)
    entry = entry_node(graph)
    hud_get = variable_getter(graph, "PrototypeHUD", -300, 250)
    call = context_method_node(graph, hud_get, [hud_function], 0, 0)
    connect(entry, ["then"], call, ["execute", "exec"])
    for _, param_name, _ in params:
        if find_pin(call, "in", [param_name], required=False):
            connect(entry, [param_name], call, [param_name])
    return graph


def bind_dispatcher(graph, exec_source_node, exec_source_alias, target_get, dispatcher_name, handler, x, y):
    bind = create(
        graph, [f"Bind Event to {dispatcher_name}", dispatcher_name], x, y,
        include=("bind", norm(dispatcher_name)),
    )
    create_event = create(
        graph, ["CreateEvent", "Create Event", "创建事件"], x - 50, y + 240,
        output_words=("OutputDelegate",),
    )
    connect(exec_source_node, [exec_source_alias], bind, ["execute", "exec"])
    connect(
        target_get,
        ["value", "Item", "Array Element", "ArrayElement", "数组元素", "Output_Get", "Output", target_get.get_node_title()],
        bind,
        ["target", "self"],
    )
    connect(create_event, ["ReturnValue", "OutputDelegate"], bind, ["Event", "Delegate"])
    set_default(create_event, ["Object", "self"], "self")
    BlueprintTools.set_create_event_function(create_event, handler)
    return bind, create_event


def clear_character_t04_nodes(character):
    graph = unreal.BlueprintEditorLibrary.find_event_graph(character)
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    stale = []
    for node in editor.list_all_nodes():
        try:
            if str(node.get_editor_property("node_comment")) == TAG:
                stale.append(node)
        except Exception:
            pass
    if stale:
        editor.remove_nodes(stale)


def build_character(wallet, hud, box, interaction, outcome_type):
    character = load(CHARACTER_PATH)
    compile_and_save(character)
    cdo = unreal.get_default_object(character.generated_class())
    wallet_components = [
        component for component in ActorTools.get_components(cdo)
        if unreal.MathLibrary.class_is_child_of(component.get_class(), wallet.generated_class())
    ]
    if not wallet_components:
        kept_wallet = ActorTools.add_component(character, wallet.generated_class(), "BPC_Wallet")
    else:
        kept_wallet = next(
            (component for component in wallet_components if component.get_name() == "BPC_Wallet_GEN_VARIABLE"),
            wallet_components[0],
        )
        for duplicate in wallet_components:
            if duplicate != kept_wallet:
                ActorTools.remove_component(duplicate)
    wallet_component_name = kept_wallet.get_name().removesuffix("_GEN_VARIABLE")
    compile_and_save(character)
    hud_type = unreal.BlueprintEditorLibrary.get_object_reference_type(hud.generated_class())
    ensure_variable(character, "PrototypeHUD", hud_type, False)
    compile_and_save(character)

    build_handler(character, "HandleMoneyChanged", (
        ("basic", "NewMoney", "int"), ("basic", "Delta", "int")
    ), "UpdateMoney")
    build_handler(character, "HandleFocusChanged", (
        ("object", "FocusedActor", unreal.Actor.static_class()),
    ), "UpdateFocus")
    build_handler(character, "HandleOutcomeResolved", (
        ("enum", "Outcome", outcome_type),
        ("object", "SpawnedActor", unreal.Actor.static_class()),
        ("basic", "bSpawnSucceeded", "bool"),
    ), "ShowOutcome")
    compile_and_save(character)

    clear_character_t04_nodes(character)
    graph = unreal.BlueprintEditorLibrary.find_event_graph(character)
    begin = BlueprintTools.add_event(character, "ReceiveBeginPlay", unreal.IntPoint(-1800, -300))
    _tag(begin)
    create_widget = create(
        graph,
        ["CreateWidget", "Create Widget", "创建控件", "创建Widget", "控件", "UserWidget"],
        -1500,
        -300,
        input_words=("Class",),
        output_words=("ReturnValue",),
    )
    set_default(create_widget, ["Class"], hud.generated_class().get_path_name())
    connect(begin, ["then"], create_widget, ["execute", "exec"])
    valid_test = pure_is_valid(graph, -1300, 0)
    connect(create_widget, ["ReturnValue"], valid_test, ["InputObject", "Object"])
    valid = create(
        graph, ["工具|流程控制|分支", "Branch", "分支"], -1250, -300,
        include=("流程控制", "分支"),
    )
    connect(create_widget, ["then"], valid, ["execute", "exec"])
    connect(valid_test, ["ReturnValue"], valid, ["Condition"])
    error = create(graph, ["PrintString"], -1000, -550, include=("printstring",))
    set_default(error, ["InString", "String"], "[HUD] ERROR WBP_PrototypeHUD creation failed")
    set_default(error, ["PrintToLog"], "true")
    set_default(error, ["PrintToScreen"], "true")
    connect(valid, ["False", "else"], error, ["execute", "exec"])
    hud_set = variable_setter(graph, "PrototypeHUD", -1000, -300)
    connect(valid, ["True", "then"], hud_set, ["execute", "exec"])
    connect(create_widget, ["ReturnValue"], hud_set, ["PrototypeHUD", "value"])
    add_view = create(graph, ["AddToViewport"], -750, -300, include=("addtoviewport",))
    connect(hud_set, ["then"], add_view, ["execute", "exec"])
    connect(create_widget, ["ReturnValue"], add_view, ["target", "self"])

    wallet_get = component_getter(graph, wallet_component_name, -850, 120)
    get_money = create(graph, ["GetMoney"], -600, 100, include=("getmoney",), output_words=("MoneyValue",))
    connect(wallet_get, ["BPC_Wallet", "value"], get_money, ["target", "self"])
    init_money = create(graph, ["UpdateMoney"], -500, -300, include=("updatemoney",))
    connect(add_view, ["then"], init_money, ["execute", "exec"])
    connect(create_widget, ["ReturnValue"], init_money, ["target", "self"])
    connect(get_money, ["MoneyValue", "ReturnValue"], init_money, ["NewMoney"])

    bind_money, money_event = bind_dispatcher(
        graph, init_money, "then", wallet_get, "OnMoneyChanged", "HandleMoneyChanged", -200, -300
    )
    interaction_get = component_getter(graph, "BPC_Interaction", -250, 120)
    bind_focus, focus_event = bind_dispatcher(
        graph, bind_money, "then", interaction_get, "OnFocusedActorChanged", "HandleFocusChanged", 100, -300
    )

    get_all = create(
        graph, ["GetAllActorsOfClass", "Get All Actors Of Class"], 400, -300,
        include=("getallactorsofclass",), input_words=("ActorClass",), output_words=("OutActors",),
    )
    set_default(get_all, ["ActorClass"], box.generated_class().get_path_name())
    connect(bind_focus, ["then"], get_all, ["execute", "exec"])
    actors_pin = find_pin(get_all, "out", ["OutActors"])
    array_get = context_node_from_pin(
        graph,
        actors_pin,
        ["Array Get", "Get (a copy)", "获取", "数组"],
        650,
        50,
        ["Index", "Dimension 1", "Dimension1"],
        ["Item", "Array Element", "ArrayElement", "数组元素", "Output_Get", "Output"],
    )
    set_default(array_get, ["Index", "Dimension 1", "Dimension1"], "0")
    bind_outcome, outcome_event = bind_dispatcher(
        graph, get_all, "then", array_get, "OnOutcomeResolved", "HandleOutcomeResolved", 700, -300
    )
    BlueprintTools.arrange_nodes(BlueprintTools.find_nodes(graph))
    for create_event_node, handler in (
        (money_event, "HandleMoneyChanged"),
        (focus_event, "HandleFocusChanged"),
        (outcome_event, "HandleOutcomeResolved"),
    ):
        BlueprintTools.set_create_event_function(create_event_node, handler)
        if BlueprintTools.get_create_event_function(create_event_node) != handler:
            fail(f"Create Event did not retain handler {handler}")
    compile_and_save(character)
    log("Modified BP_FirstPersonCharacter with wallet, HUD creation, and event bindings")
    return character


def main():
    log("Starting official-Python T04 build (no MCP, no PIE)")
    outcome_enum = load(OUTCOME_PATH)
    outcome_type = enum_pin_type(outcome_enum)
    interaction = load(INTERACTION_PATH)
    wallet = build_wallet()
    high = build_loot(HIGH_PATH, GOLD_MESH_PATH, (1.0, 1.0, 1.0), (0.0, 0.0, 0.0))
    trash = build_loot(TRASH_PATH, CHAIR_MESH_PATH, (0.65, 0.65, 0.65), (0.0, 90.0, -8.0))
    hud = build_hud(outcome_enum, outcome_type)
    box = build_box(wallet, high, trash)
    build_character(wallet, hud, box, interaction, outcome_type)
    log("BUILD PASS - T04 assets compiled and saved; PIE acceptance remains")


if __name__ == "__main__":
    main()
