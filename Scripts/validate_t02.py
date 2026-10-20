"""Structural validation for T02. Run inside Unreal; this does not start PIE."""

import unreal

from editor_toolset.toolsets.actor import ActorTools
from editor_toolset.toolsets.blueprint import BlueprintTools


PREFIX = "[T02Validate]"
BOX_PATH = "/Game/Anomalies/Containers/BP_AnomalyBox"
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
failures = []


def check(condition, message):
    if condition:
        unreal.log(f"{PREFIX} PASS {message}")
    else:
        unreal.log_error(f"{PREFIX} FAIL {message}")
        failures.append(message)


box = ASSETS.load_asset(BOX_PATH)
check(box is not None, "BP_AnomalyBox exists")

if box is not None:
    BlueprintTools.compile_blueprint(box, warnings_as_errors=False)
    cdo = unreal.get_default_object(box.generated_class())
    components = {item.get_name(): item for item in ActorTools.get_components(cdo)}
    for name in ("CrateMesh", "LootSpawnPoint", "CreatureSpawnPoint"):
        check(any(name.lower() in item.lower() for item in components), f"component exists: {name}")

    variables = {str(item) for item in unreal.BlueprintEditorLibrary.list_member_variable_names(box)}
    for name in ("bOpened", "bResolved", "RevealDelay", "bDebugLogging"):
        check(name in variables, f"variable exists: {name}")
    check(abs(float(cdo.get_editor_property("RevealDelay")) - 1.0) < 0.001, "RevealDelay defaults to 1.0")
    check(not bool(cdo.get_editor_property("bOpened")), "bOpened defaults false")
    check(not bool(cdo.get_editor_property("bResolved")), "bResolved defaults false")
    check(bool(cdo.get_editor_property("bDebugLogging")), "bDebugLogging defaults true")

    dispatchers = {str(item) for item in unreal.BlueprintEditorLibrary.list_event_dispatchers(box)}
    check("OnBoxOpened" in dispatchers, "OnBoxOpened dispatcher exists")
    check("OnOutcomeResolved" in dispatchers, "OnOutcomeResolved dispatcher exists")

    event_graph = unreal.BlueprintEditorLibrary.find_event_graph(box)
    event_editor = unreal.BlueprintGraphEditor.get_graph_editor(event_graph)
    rows = []
    event_nodes = BlueprintTools.find_nodes(event_graph)
    for node in event_nodes:
        info = BlueprintTools._get_node_info(node)
        pin_rows = []
        for pin in (
            list(unreal.BlueprintEditorLibrary.list_input_pins(node))
            + list(unreal.BlueprintEditorLibrary.list_output_pins(node))
        ):
            name = str(unreal.BlueprintGraphPinLibrary.get_pin_name(pin))
            try:
                value = str(pin.get_pin_value())
            except Exception:
                value = ""
            pin_rows.append(f"{name}={value}")
        rows.append(f"{info.type_id}|{node.get_node_title()}|{'|'.join(pin_rows)}".lower())
    graph_text = "\n".join(rows)
    orphan_names = ("onmapopened", "onmediaopened", "onboxopened")
    orphan_custom_events = [
        node
        for node in event_nodes
        if isinstance(node, unreal.K2Node_CustomEvent)
        and any(name in "".join(ch.lower() for ch in str(node.get_node_title()) if ch.isalnum()) for name in orphan_names)
    ]
    check(not orphan_custom_events, "no stale dispatcher-search custom events")
    check(not event_editor.list_nodes_with_errors(), "EventGraph has no nodes with compile errors")
    for token, description in (
        ("interact", "Interact event"),
        ("分支", "duplicate-open branch"),
        ("bopened", "bOpened guard/set"),
        ("setcollisionresponsetochannel", "Visibility response disable"),
        ("onboxopened", "OnBoxOpened call"),
        ("playanimation", "opening animation call"),
        ("playsoundatlocation", "opening sound call"),
        ("delay", "reveal delay"),
        ("resolveoutcome reached", "post-delay resolve log"),
    ):
        check(token in graph_text, description)

if failures:
    raise RuntimeError(f"{PREFIX} STRUCTURAL FAIL ({len(failures)}): {failures}")
unreal.log(f"{PREFIX} STRUCTURAL PASS - PIE acceptance remains")
