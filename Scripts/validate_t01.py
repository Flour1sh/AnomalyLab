"""Non-PIE structural validation for T01. Run inside Unreal after build_t01.py."""

import unreal

from editor_toolset.toolsets.blueprint import BlueprintTools


PREFIX = "[T01Validate]"
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

PATHS = {
    "bpi": "/Game/Interaction/BPI_Interactable",
    "component": "/Game/Core/Components/BPC_Interaction",
    "action": "/Game/Core/Input/IA_Interact",
    "context": "/Game/Core/Input/IMC_Prototype",
    "box": "/Game/Anomalies/Containers/BP_AnomalyBox",
    "character": "/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter",
    "controller": "/Game/FirstPerson/Blueprints/BP_FirstPersonPlayerController",
}

failures = []


def check(condition, message):
    if condition:
        unreal.log(f"{PREFIX} PASS {message}")
    else:
        unreal.log_error(f"{PREFIX} FAIL {message}")
        failures.append(message)


def load(path):
    result = ASSETS.load_asset(path)
    check(result is not None, f"asset exists {path}")
    return result


def graph_text(blueprint):
    rows = []
    for graph_name in unreal.BlueprintEditorLibrary.list_graph_names(blueprint):
        target = unreal.BlueprintEditorLibrary.find_graph(blueprint, graph_name)
        if target is None:
            continue
        for node in BlueprintTools.find_nodes(target):
            info = BlueprintTools._get_node_info(node)
            pins = [
                str(unreal.BlueprintGraphPinLibrary.get_pin_name(pin))
                for pin in (
                    list(unreal.BlueprintEditorLibrary.list_input_pins(node))
                    + list(unreal.BlueprintEditorLibrary.list_output_pins(node))
                )
            ]
            rows.append(f"{graph_name}|{info.type_id}|{node.get_node_title()}|{'|'.join(pins)}")
    return "\n".join(rows).lower()


def mapping_context_defaults(blueprint):
    values = []
    for graph_name in unreal.BlueprintEditorLibrary.list_graph_names(blueprint):
        target = unreal.BlueprintEditorLibrary.find_graph(blueprint, graph_name)
        if target is None:
            continue
        for node in BlueprintTools.find_nodes(target):
            marker = f"{BlueprintTools._get_node_info(node).type_id} {node.get_node_title()}"
            if "addmappingcontext" not in "".join(ch.lower() for ch in marker if ch.isalnum()):
                continue
            for pin in unreal.BlueprintEditorLibrary.list_input_pins(node):
                name = str(unreal.BlueprintGraphPinLibrary.get_pin_name(pin))
                if name == "MappingContext":
                    values.append(str(pin.get_pin_value()))
    return values


assets = {name: load(path) for name, path in PATHS.items()}
if all(assets.values()):
    bpi = assets["bpi"]
    component = assets["component"]
    box = assets["box"]
    character = assets["character"]
    controller = assets["controller"]
    action = assets["action"]
    context = assets["context"]

    check("Interact" in {str(item) for item in unreal.BlueprintEditorLibrary.list_graph_names(bpi)},
          "BPI has Interact")
    interact_graph = unreal.BlueprintEditorLibrary.find_graph(bpi, unreal.Name("Interact"))
    entry = next(
        (node for node in BlueprintTools.find_nodes(interact_graph)
         if isinstance(node, unreal.K2Node_FunctionEntry)), None
    )
    entry_outputs = (
        [str(unreal.BlueprintGraphPinLibrary.get_pin_name(pin))
         for pin in unreal.BlueprintEditorLibrary.list_output_pins(entry)] if entry else []
    )
    check("Interactor" in entry_outputs, "Interact signature includes Interactor")

    check(action.get_editor_property("value_type") == unreal.InputActionValueType.BOOLEAN,
          "IA_Interact is Boolean")
    mapping_data = context.get_editor_property("default_key_mappings")
    mappings = list(mapping_data.get_editor_property("mappings"))
    check(len(mappings) == 1, "IMC_Prototype contains one independent mapping")
    if mappings:
        check(str(mappings[0].get_editor_property("key").get_editor_property("key_name")) == "E",
              "IMC_Prototype maps E")

    cdo = unreal.get_default_object(component.generated_class())
    check(abs(float(cdo.get_editor_property("InteractionDistance")) - 300.0) < 0.001,
          "interaction distance is 300 cm")
    check(all(name in {str(item) for item in unreal.BlueprintEditorLibrary.list_graph_names(component)}
              for name in ("TraceForInteractable", "UpdateFocus", "TryInteract")),
          "component owns all T01 functions")

    component_nodes = graph_text(component)
    check("linetrace" in component_nodes, "component uses a line trace")
    check("implementinterface" in component_nodes, "trace checks interface implementation")
    check("tryinteract" in component_nodes and "traceforinteractable" in component_nodes,
          "TryInteract performs a fresh trace")
    check("message" in component_nodes and "interact" in component_nodes,
          "TryInteract calls Interact as an interface message")
    check("casttobp_anomalybox" not in component_nodes, "component has no cast to BP_AnomalyBox")
    check("eventtick" in component_nodes and "updatefocus" in component_nodes,
          "Event Tick routes to UpdateFocus")
    check("onfocusedactorchanged" in component_nodes, "focus-change dispatcher is called")

    box_cdo = unreal.get_default_object(box.generated_class())
    iface = bpi.generated_class()
    try:
        implements = unreal.SystemLibrary.does_implement_interface(box_cdo, iface)
    except Exception:
        implements = box_cdo.get_class().implements_interface(iface)
    check(bool(implements), "BP_AnomalyBox implements BPI_Interactable")
    box_nodes = graph_text(box)
    check("interact" in box_nodes and "printstring" in box_nodes,
          "box Interact only supplies confirmation logging")

    character_nodes = graph_text(character)
    check("ia_interact" in character_nodes and "started" in character_nodes,
          "Character routes IA_Interact Started")
    check("tryinteract" in character_nodes, "Character calls BPC_Interaction.TryInteract")
    check("casttobp_anomalybox" not in character_nodes, "Character has no cast to BP_AnomalyBox")
    check(all(token in character_nodes for token in ("ia_move", "ia_look", "ia_jump")),
          "existing move/look/jump input nodes remain")

    context_defaults = mapping_context_defaults(controller)
    check(any("IMC_Prototype" in item for item in context_defaults),
          "PlayerController adds IMC_Prototype")
    check(any("IMC_Default" in item for item in context_defaults),
          "PlayerController preserves the template mapping context")

    for blueprint in (bpi, component, box, character, controller):
        BlueprintTools.compile_blueprint(blueprint, warnings_as_errors=False)
        check(ASSETS.save_loaded_asset(blueprint, only_if_is_dirty=False),
              f"compiled and saved {blueprint.get_name()}")

    check(bool(LEVELS.load_level("/Game/Prototype/Maps/L_Prototype")), "L_Prototype loads")
    placed = [actor for actor in ACTORS.get_all_level_actors()
              if actor.get_actor_label() == "PROTOTYPE_AnomalyBox_T01"]
    check(len(placed) == 1, "exactly one T01 anomaly box is placed")

if failures:
    raise RuntimeError(f"{PREFIX} FAILED ({len(failures)}): {failures}")
unreal.log(f"{PREFIX} STRUCTURAL PASS - PIE acceptance checks remain")
