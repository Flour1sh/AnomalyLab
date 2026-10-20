"""Structural validation for T03. Run inside Unreal; this does not start PIE."""

import unreal

from editor_toolset.toolsets.blueprint import BlueprintTools


PREFIX = "[T03Validate]"
BOX_PATH = "/Game/Anomalies/Containers/BP_AnomalyBox"
OUTCOME_PATH = "/Game/Core/Types/EAnomalyOutcome"
ASSETS = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
failures = []


def norm(value):
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def check(condition, message):
    if condition:
        unreal.log(f"{PREFIX} PASS {message}")
    else:
        unreal.log_error(f"{PREFIX} FAIL {message}")
        failures.append(message)


box = ASSETS.load_asset(BOX_PATH)
enum_asset = ASSETS.load_asset(OUTCOME_PATH)
check(box is not None, "BP_AnomalyBox exists")
check(enum_asset is not None, "EAnomalyOutcome exists")

if box is not None and enum_asset is not None:
    BlueprintTools.compile_blueprint(box, warnings_as_errors=False)
    graph = unreal.BlueprintEditorLibrary.find_event_graph(box)
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    check(not editor.list_nodes_with_errors(), "EventGraph has no compile errors")

    variables = {str(item) for item in unreal.BlueprintEditorLibrary.list_member_variable_names(box)}
    for name in ("bForceOutcome", "ForcedOutcome", "OutcomeRoll"):
        check(name in variables, f"variable exists: {name}")
    cdo = unreal.get_default_object(box.generated_class())
    check(not bool(cdo.get_editor_property("bForceOutcome")), "bForceOutcome defaults false")

    rows = []
    switch_outputs = []
    delegate_calls = 0
    print_calls = 0
    for node in BlueprintTools.find_nodes(graph):
        title = str(node.get_node_title())
        normalized_title = norm(title)
        if "onoutcomeresolved" in normalized_title:
            delegate_calls += 1
        if "printstring" in normalized_title or "打印字符串" in title:
            print_calls += 1
        pins = []
        for pin in (
            list(unreal.BlueprintEditorLibrary.list_input_pins(node))
            + list(unreal.BlueprintEditorLibrary.list_output_pins(node))
        ):
            name = str(unreal.BlueprintGraphPinLibrary.get_pin_name(pin))
            try:
                value = str(pin.get_pin_value())
            except Exception:
                value = ""
            pins.append(f"{name}={value}")
        rows.append(f"{title}|{'|'.join(pins)}".lower())
        if "switchoneanomalyoutcome" in norm(title):
            switch_outputs = [
                str(unreal.BlueprintGraphPinLibrary.get_pin_name(pin))
                for pin in unreal.BlueprintEditorLibrary.list_output_pins(node)
            ]

    graph_text = "\n".join(rows)
    check(switch_outputs == ["NewEnumerator0", "NewEnumerator1", "NewEnumerator2"],
          "EAnomalyOutcome exposes three ordered entries")
    check(delegate_calls == 6, "six outcome dispatcher calls exist")
    check(print_calls >= 6, "six outcome log calls exist")
    for token, description in (
        ("randomintegerinrange", "Random Integer in Range node"),
        ("min=0", "random minimum is 0"),
        ("max=2", "random maximum is 2"),
        ("forced outcome=highvalue", "forced HighValue log path"),
        ("forced outcome=trash", "forced Trash log path"),
        ("forced outcome=threat", "forced Threat log path"),
        ("roll=0 outcome=highvalue", "random HighValue log path"),
        ("roll=1 outcome=trash", "random Trash log path"),
        ("roll=2 outcome=threat", "random Threat log path"),
    ):
        check(token in graph_text, description)
    check("resolveoutcome reached" not in graph_text, "T02 placeholder removed")

if failures:
    raise RuntimeError(f"{PREFIX} STRUCTURAL FAIL ({len(failures)}): {failures}")
unreal.log(f"{PREFIX} STRUCTURAL PASS - PIE acceptance remains")
