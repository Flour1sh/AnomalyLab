"""Build T03 random/forced outcome selection through Unreal's Python API.

Run this inside the Unreal Editor. It modifies only BP_AnomalyBox and does not
start PIE. EAnomalyOutcome must already contain three entries in this order:
HighValue, Trash, Threat.
"""

import importlib
import sys
from pathlib import Path

import unreal

from editor_toolset.toolsets.blueprint import BlueprintTools


PREFIX = "[T03]"
TAG = "T03_GENERATED"
BOX_PATH = "/Game/Anomalies/Containers/BP_AnomalyBox"
OUTCOME_PATH = "/Game/Core/Types/EAnomalyOutcome"
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
SCRIPT_DIR = str(Path(__file__).resolve().parent)


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


def node_type(graph, searches, include=(), exclude=(), input_words=(), output_words=()):
    include = tuple(norm(item) for item in include)
    exclude = tuple(norm(item) for item in exclude)
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
            try:
                info = BlueprintTools.get_node_type_pins(graph, candidate)
                inputs = {norm(item.name) for item in info.input_pins}
                outputs = {norm(item.name) for item in info.output_pins}
            except Exception:
                continue
            if not all(any(word in name or name in word for name in inputs) for word in input_words):
                continue
            if not all(any(word in name or name in word for name in outputs) for word in output_words):
                continue
            return candidate
    fail(f"No node type matched {searches}; candidates={seen[:40]}")


def create(graph, searches, x, y, include=(), exclude=(), input_words=(), output_words=()):
    type_id = node_type(graph, searches, include, exclude, input_words, output_words)
    node = BlueprintTools.create_node(graph, type_id, unreal.IntPoint(x, y))
    try:
        node.set_editor_property("node_comment", TAG)
    except Exception:
        pass
    return node


def compile_and_save(blueprint):
    BlueprintTools.compile_blueprint(blueprint, warnings_as_errors=False)
    graph = unreal.BlueprintEditorLibrary.find_event_graph(blueprint)
    errors = unreal.BlueprintGraphEditor.get_graph_editor(graph).list_nodes_with_errors()
    if errors:
        fail(f"Compile produced {len(errors)} EventGraph node errors: {[str(n.get_node_title()) for n in errors]}")
    if not ASSETS.save_loaded_asset(blueprint, only_if_is_dirty=False):
        fail(f"Could not save {blueprint.get_path_name()}")


def variable_names(blueprint):
    return {str(item) for item in unreal.BlueprintEditorLibrary.list_member_variable_names(blueprint)}


def ensure_variable(blueprint, name, pin_type, editable):
    if name not in variable_names(blueprint):
        if not unreal.BlueprintEditorLibrary.add_member_variable(blueprint, name, pin_type):
            fail(f"Could not add variable {name}")
    unreal.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(blueprint, name, editable)


def enum_switch_type(graph, enum_asset):
    return node_type(
        graph,
        [enum_asset.get_name(), f"Switch on {enum_asset.get_name()}"],
        include=("switch", enum_asset.get_name()),
        input_words=("Selection",),
    )


def enum_pin_type(graph, switch_type):
    probe = BlueprintTools.create_node(graph, switch_type, unreal.IntPoint(-2600, 1000))
    try:
        selection = find_pin(probe, "in", ["Selection"])
        return unreal.BlueprintGraphPinLibrary.get_pin_type(selection)
    finally:
        unreal.BlueprintGraphEditor.get_graph_editor(graph).remove_nodes([probe])


def ensure_schema(blueprint, event_graph, outcome_enum):
    switch_type = enum_switch_type(event_graph, outcome_enum)
    probe = BlueprintTools.create_node(event_graph, switch_type, unreal.IntPoint(-2600, 1000))
    try:
        outputs = [pin_name(pin) for pin in output_pins(probe)]
    finally:
        unreal.BlueprintGraphEditor.get_graph_editor(event_graph).remove_nodes([probe])
    if outputs != ["NewEnumerator0", "NewEnumerator1", "NewEnumerator2"]:
        fail(
            "EAnomalyOutcome dependency is invalid. Expected three ordered entries "
            f"HighValue/Trash/Threat; switch outputs={outputs}"
        )

    bool_type = unreal.BlueprintEditorLibrary.get_basic_type_by_name("bool")
    int_type = unreal.BlueprintEditorLibrary.get_basic_type_by_name("int")
    ensure_variable(blueprint, "bForceOutcome", bool_type, True)
    ensure_variable(blueprint, "ForcedOutcome", enum_pin_type(event_graph, switch_type), True)
    ensure_variable(blueprint, "OutcomeRoll", int_type, False)
    compile_and_save(blueprint)
    cdo = unreal.get_default_object(blueprint.generated_class())
    cdo.set_editor_property("bForceOutcome", False)
    cdo.set_editor_property("OutcomeRoll", 0)
    compile_and_save(blueprint)
    return switch_type


def rebuild_t02_graph(blueprint):
    """Reset this script-owned EventGraph, then recreate the accepted T02 flow."""
    graph = unreal.BlueprintEditorLibrary.find_event_graph(blueprint)
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    existing = list(editor.list_all_nodes())
    if existing:
        editor.remove_nodes(existing)
    if SCRIPT_DIR not in sys.path:
        sys.path.insert(0, SCRIPT_DIR)
    import build_t02
    importlib.reload(build_t02)
    build_t02.build_event_graph(blueprint)
    log("Rebuilt the accepted T02 EventGraph before applying T03")


def clear_previous_t03(graph):
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    stale = []
    for node in editor.list_all_nodes():
        try:
            comment = str(node.get_editor_property("node_comment"))
        except Exception:
            comment = ""
        title = norm(node.get_node_title())
        if (
            comment == TAG
            or "resolveoutcomereached" in title
            or "switchoneanomalyoutcome" in title
            or "switchonint" in title
            or "silencewarningonunresolvedpath" in title
            or ("onoutcomeresolved" in title and "callonoutcomeresolved" not in title)
        ):
            stale.append(node)
            continue
        for pin in input_pins(node):
            try:
                value = norm(pin.get_pin_value())
            except Exception:
                value = ""
            if "resolveoutcomereached" in value:
                stale.append(node)
                break
    if stale:
        editor.remove_nodes(stale)


def find_reveal_delay(graph):
    candidates = []
    for node in BlueprintTools.find_nodes(graph):
        names_in = {norm(pin_name(pin)) for pin in input_pins(node)}
        names_out = {norm(pin_name(pin)) for pin in output_pins(node)}
        title = norm(node.get_node_title())
        if (
            "duration" in names_in
            and ("completed" in names_out or "then" in names_out)
            and ("delay" in title or "延迟" in str(node.get_node_title()))
        ):
            candidates.append(node)
    if len(candidates) != 1:
        fail(f"Expected one Reveal Delay node, found {len(candidates)}")
    return candidates[0]


def variable_getter(graph, name, x, y):
    friendly = name[1:] if name.startswith("b") and len(name) > 1 and name[1].isupper() else name
    wanted = {norm(name), norm(friendly)}
    wanted_tails = {
        norm("Get " + name), norm("Get " + friendly),
        norm("获取" + name), norm("获取" + friendly),
    }
    for search in (name, friendly):
        for candidate in BlueprintTools.find_node_types(graph, search):
            # Some searches also return dispatcher/custom-event entries. Merely
            # asking those entries for pin metadata can instantiate orphan nodes,
            # so reject anything that is not explicitly a variable getter first.
            if norm(str(candidate).split("|")[-1]) not in wanted_tails:
                continue
            try:
                info = BlueprintTools.get_node_type_pins(graph, candidate)
                outputs = {norm(item.name) for item in info.output_pins}
                inputs = {norm(item.name) for item in info.input_pins}
            except Exception:
                continue
            if outputs & wanted and "execute" not in inputs:
                node = BlueprintTools.create_node(graph, candidate, unreal.IntPoint(x, y))
                try:
                    node.set_editor_property("node_comment", TAG)
                except Exception:
                    pass
                return node
    fail(f"Could not find exact getter for {name}")


def variable_setter(graph, name, x, y):
    friendly = name[1:] if name.startswith("b") and len(name) > 1 and name[1].isupper() else name
    wanted = {norm(name), norm(friendly)}
    wanted_tails = {
        norm("Set " + name), norm("Set " + friendly),
        norm("设置" + name), norm("设置" + friendly),
    }
    for search in (name, friendly):
        for candidate in BlueprintTools.find_node_types(graph, search):
            if norm(str(candidate).split("|")[-1]) not in wanted_tails:
                continue
            try:
                info = BlueprintTools.get_node_type_pins(graph, candidate)
                inputs = {norm(item.name) for item in info.input_pins}
                outputs = {norm(item.name) for item in info.output_pins}
            except Exception:
                continue
            if inputs & wanted and "execute" in inputs and "then" in outputs:
                node = BlueprintTools.create_node(graph, candidate, unreal.IntPoint(x, y))
                try:
                    node.set_editor_property("node_comment", TAG)
                except Exception:
                    pass
                return node
    fail(f"Could not find exact setter for {name}")


def branch(graph, x, y):
    return create(
        graph, ["工具|流程控制|分支", "Branch", "分支"], x, y,
        include=("流程控制", "分支"),
    )


def int_equal(graph, x, y):
    return create(
        graph, ["工具|运算符|等于（==）", "Equal"], x, y,
        include=("等于",), input_words=("A", "B"), output_words=("ReturnValue",),
    )


def int_switch_type(graph):
    seen = []
    for search in ("切换", "Switch", "整数", "Int"):
        for candidate in BlueprintTools.find_node_types(graph, search):
            if candidate in seen:
                continue
            seen.append(candidate)
            lowered = norm(candidate)
            tail = norm(candidate.split("|")[-1])
            if not (
                tail.startswith("switchonint")
                or "switchon整数" in tail
                or "以整数切换" in tail
                or tail == "切换整型"
            ):
                continue
            try:
                info = BlueprintTools.get_node_type_pins(graph, candidate)
                inputs = {norm(item.name) for item in info.input_pins}
                outputs = {norm(item.name) for item in info.output_pins}
            except Exception:
                continue
            if "execute" in inputs and "selection" in inputs and "default" in outputs:
                return candidate
    matching = [item for item in seen if "switch" in norm(item) or "切换" in norm(item)]
    fail(f"Could not find Switch on Int; switch candidates={matching[:80]}")


def outcome_tail(graph, x, y, message, enum_internal_name):
    printer = create(graph, ["Development|PrintString", "PrintString"], x, y, include=("printstring",))
    set_default(printer, ["InString", "String"], message)
    set_default(printer, ["PrintToScreen"], "false")
    set_default(printer, ["PrintToLog"], "true")

    resolved = variable_setter(graph, "bResolved", x + 260, y)
    set_default(resolved, ["bResolved", "Resolved", "value"], "true")
    dispatch = BlueprintTools.create_node(
        graph, "默认|CallOnOutcomeResolved", unreal.IntPoint(x + 520, y)
    )
    try:
        dispatch.set_editor_property("node_comment", TAG)
    except Exception:
        pass
    set_default(dispatch, ["Outcome"], enum_internal_name)
    set_default(dispatch, ["bSpawnSucceeded", "SpawnSucceeded"], "false")
    connect(printer, ["then"], resolved, ["execute", "exec"])
    connect(resolved, ["then"], dispatch, ["execute", "exec"])
    return printer


def build_graph(blueprint, switch_type):
    graph = unreal.BlueprintEditorLibrary.find_event_graph(blueprint)
    clear_previous_t03(graph)
    delay = find_reveal_delay(graph)

    get_resolved = variable_getter(graph, "bResolved", 1000, 300)
    resolved_guard = branch(graph, 1250, 0)
    get_force = variable_getter(graph, "bForceOutcome", 1500, 300)
    force_branch = branch(graph, 1750, 0)
    connect(delay, ["Completed", "then"], resolved_guard, ["execute", "exec"])
    connect(get_resolved, ["bResolved", "Resolved", "value"], resolved_guard, ["Condition"])
    connect(resolved_guard, ["False", "else"], force_branch, ["execute", "exec"])
    connect(get_force, ["bForceOutcome", "ForceOutcome", "value"], force_branch, ["Condition"])

    # Forced path: use the enum switch so all three editor-selectable values are explicit.
    forced_get = variable_getter(graph, "ForcedOutcome", 1950, -500)
    forced_switch = BlueprintTools.create_node(graph, switch_type, unreal.IntPoint(2200, -500))
    try:
        forced_switch.set_editor_property("node_comment", TAG)
    except Exception:
        pass
    connect(force_branch, ["then", "True"], forced_switch, ["execute", "exec"])
    connect(forced_get, ["ForcedOutcome", "value"], forced_switch, ["Selection"])
    forced_specs = (
        ("NewEnumerator0", "HighValue", -650),
        ("NewEnumerator1", "Trash", -400),
        ("NewEnumerator2", "Threat", -150),
    )
    for internal, display, y in forced_specs:
        tail = outcome_tail(graph, 2550, y, f"[Box] Forced Outcome={display}", internal)
        connect(forced_switch, [internal], tail, ["execute", "exec"])

    # Random path: cache exactly one roll, then map 0/1/2 without anti-repeat logic.
    random_node = create(
        graph, ["RandomIntegerInRange", "Random Integer in Range"], 1950, 350,
        include=("randomintegerinrange",), exclude=("stream",), output_words=("ReturnValue",),
    )
    set_default(random_node, ["Min"], "0")
    set_default(random_node, ["Max"], "2")
    set_roll = variable_setter(graph, "OutcomeRoll", 2200, 150)
    connect(force_branch, ["False", "else"], set_roll, ["execute", "exec"])
    connect(random_node, ["ReturnValue", "value"], set_roll, ["OutcomeRoll", "value"])

    switch_int_type = int_switch_type(graph)
    roll_switch = BlueprintTools.create_node(graph, switch_int_type, unreal.IntPoint(2700, 150))
    try:
        roll_switch.set_editor_property("node_comment", TAG)
    except Exception:
        pass
    BlueprintTools.add_node_pin(roll_switch)
    BlueprintTools.add_node_pin(roll_switch)
    connect(set_roll, ["then"], roll_switch, ["execute", "exec"])
    connect(set_roll, ["OutcomeRoll", "value", "Output_Get"], roll_switch, ["Selection"])

    random_specs = (
        (roll_switch, "0", "NewEnumerator0", "HighValue", 50),
        (roll_switch, "1", "NewEnumerator1", "Trash", 300),
        (roll_switch, "Default", "NewEnumerator2", "Threat", 550),
    )
    for source, exec_pin, internal, display, y in random_specs:
        roll = {"HighValue": 0, "Trash": 1, "Threat": 2}[display]
        tail = outcome_tail(graph, 3950, y, f"[Box] Roll={roll} Outcome={display}", internal)
        connect(source, [exec_pin], tail, ["execute", "exec"])

    BlueprintTools.arrange_nodes(BlueprintTools.find_nodes(graph))


def main():
    log("Starting official-Python T03 build (no MCP graph edits, no PIE)")
    box = load(BOX_PATH)
    outcome_enum = load(OUTCOME_PATH)
    rebuild_t02_graph(box)
    graph = unreal.BlueprintEditorLibrary.find_event_graph(box)
    clear_previous_t03(graph)
    switch_type = ensure_schema(box, graph, outcome_enum)
    build_graph(box, switch_type)
    compile_and_save(box)
    log("BUILD PASS - BP_AnomalyBox compiled and saved; PIE acceptance remains")


main()
