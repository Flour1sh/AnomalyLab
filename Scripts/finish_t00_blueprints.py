import unreal


asset_subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
pin_library = unreal.BlueprintGraphPinLibrary


def log(message):
    unreal.log(f"[T00Blueprint] {message}")


blueprint = asset_subsystem.load_asset("/Game/Core/Debug/BFL_PrototypeLog")
if blueprint is None:
    raise RuntimeError("BFL_PrototypeLog is missing")

string_type = unreal.BlueprintEditorLibrary.get_basic_type_by_name("String")

for function_name, print_to_screen in (("Info", False), ("Warning", True), ("Error", True)):
    editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(blueprint, function_name)
    if editor is None:
        raise RuntimeError(f"Could not access graph editor for {function_name}")

    nodes = editor.list_all_nodes()
    call_nodes = [node for node in nodes if isinstance(node, unreal.K2Node_CallFunction)]
    if call_nodes:
        log(f"{function_name} already contains a call node")
        continue

    message_pin = editor.add_graph_input_parameter("Message", string_type, "")
    print_node = editor.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    if print_node is None:
        raise RuntimeError(f"Could not add Print String node to {function_name}")

    entry_exec = editor.find_graph_entry_pin()
    node_exec = print_node.find_execute_pin()
    node_message = print_node.find_input_pin("InString")
    if not pin_library.try_create_connection(entry_exec, node_exec):
        raise RuntimeError(f"Could not connect execution pins in {function_name}")
    if not pin_library.try_create_connection(message_pin, node_message):
        raise RuntimeError(f"Could not connect Message in {function_name}")

    pin_library.set_pin_value(print_node.find_input_pin("bPrintToScreen"), "true" if print_to_screen else "false")
    pin_library.set_pin_value(print_node.find_input_pin("bPrintToLog"), "true")
    duration_pin = print_node.find_input_pin("Duration")
    if duration_pin:
        pin_library.set_pin_value(duration_pin, "4.0")
    print_node.set_node_pos(unreal.IntPoint(320, 0))
    log(f"{function_name} configured: screen={print_to_screen}, output_log=True")

unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
if unreal.BlueprintGraphEditor.get_graph_editor_by_name(blueprint, "Info").list_nodes_with_errors():
    raise RuntimeError("BFL_PrototypeLog contains graph errors after compile")
asset_subsystem.save_loaded_asset(blueprint, only_if_is_dirty=False)
log("BFL_PrototypeLog compile and save PASS")
