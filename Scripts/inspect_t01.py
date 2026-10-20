import unreal


PREFIX = "[T01Inspect]"
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)


def log(message):
    unreal.log(f"{PREFIX} {message}")


def describe_blueprint(path):
    blueprint = ASSETS.load_asset(path)
    if blueprint is None:
        log(f"MISSING {path}")
        return
    log(f"BLUEPRINT {path} class={blueprint.get_class().get_name()}")
    log(f"GRAPHS {path}: {[str(name) for name in unreal.BlueprintEditorLibrary.list_graph_names(blueprint)]}")
    log(
        f"FUNCTIONS {path}: "
        f"{[(str(item.name), bool(item.is_implemented)) for item in unreal.BlueprintEditorLibrary.list_functions(blueprint)]}"
    )
    log(
        f"EVENTS {path}: "
        f"{[(str(item.name), bool(item.is_implemented)) for item in unreal.BlueprintEditorLibrary.list_events(blueprint)]}"
    )
    generated_class = blueprint.generated_class()
    if generated_class:
        cdo = unreal.get_default_object(generated_class)
        components = cdo.get_components_by_class(unreal.ActorComponent) if isinstance(cdo, unreal.Actor) else []
        log(f"CDO COMPONENTS {path}: {[(component.get_name(), component.get_class().get_name()) for component in components]}")
    for graph_name in unreal.BlueprintEditorLibrary.list_graph_names(blueprint):
        editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(blueprint, graph_name)
        if editor is None:
            continue
        for node in editor.list_all_nodes():
            inputs = [
                (str(unreal.BlueprintGraphPinLibrary.get_pin_name(pin)), unreal.BlueprintGraphPinLibrary.get_pin_type_display_string(pin))
                for pin in unreal.BlueprintEditorLibrary.list_input_pins(node)
            ]
            outputs = [
                (str(unreal.BlueprintGraphPinLibrary.get_pin_name(pin)), unreal.BlueprintGraphPinLibrary.get_pin_type_display_string(pin))
                for pin in unreal.BlueprintEditorLibrary.list_output_pins(node)
            ]
            log(
                f"NODE {path}:{graph_name} class={node.get_class().get_name()} "
                f"title={unreal.BlueprintEditorLibrary.get_node_title(node)} inputs={inputs} outputs={outputs}"
            )


for class_name in (
    "BlueprintFactory",
    "BlueprintEditorLibrary",
    "BlueprintGraphEditor",
    "BlueprintGraphPinLibrary",
    "SubobjectDataSubsystem",
    "InputAction",
    "InputMappingContext",
    "EnhancedActionKeyMapping",
    "InputTriggerPressed",
):
    value = getattr(unreal, class_name, None)
    log(f"CLASS {class_name}: {value}")

factory = unreal.BlueprintFactory()
for property_name in ("parent_class", "blueprint_type"):
    try:
        log(f"BlueprintFactory.{property_name}={factory.get_editor_property(property_name)}")
    except Exception as exc:
        log(f"BlueprintFactory.{property_name}=UNAVAILABLE ({exc})")

describe_blueprint("/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter")
describe_blueprint("/Game/FirstPerson/Blueprints/BP_FirstPersonPlayerController")
log("INSPECTION COMPLETE")
