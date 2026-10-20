"""Read-only T04 asset/API inspection. Run through Unreal Python."""

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.actor import ActorTools


def out(label, value):
    unreal.log(f"[T04Inspect] {label}: {value}")


assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)

for path in (
    "/Game/UI/WBP_PrototypeHUD",
    "/Game/Core/Components/BPC_Wallet",
    "/Game/Anomalies/Loot/BP_Loot_HighValue",
    "/Game/Anomalies/Loot/BP_Loot_Trash",
    "/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter",
    "/Game/Anomalies/Containers/BP_AnomalyBox",
):
    obj = assets.load_asset(path)
    out(path, f"{obj} class={obj.get_class().get_name() if obj else None}")
    if obj and isinstance(obj, unreal.Blueprint):
        out(path + " variables", [str(x) for x in unreal.BlueprintEditorLibrary.list_member_variable_names(obj)])
        out(path + " dispatchers", [str(x) for x in unreal.BlueprintEditorLibrary.list_event_dispatchers(obj)])

out("UMGToolSet available", hasattr(unreal, "UMGToolSet"))
if hasattr(unreal, "UMGToolSet"):
    out("UMG methods", [x for x in dir(unreal.UMGToolSet) if not x.startswith("_")])
    out("call_method doc", unreal.UMGToolSet.call_method.__doc__)
    try:
        schema = unreal.ToolsetRegistry.get_toolset_json_schema(unreal.UMGToolSet.static_class())
        out("UMG schema", schema)
    except Exception as exc:
        out("UMG schema error", repr(exc))
    hud = assets.load_asset("/Game/UI/WBP_PrototypeHUD")
    if hud:
        try:
            info = unreal.UMGToolSet.get_widgets(hud)
            out("HUD widget count", info.info.widget_count)
            out("HUD widgets", [(str(x.widget_name), x.widget.get_class().get_name()) for x in info.widgets])
            out("HUD description", unreal.UMGToolSet.get_widget_description(hud).description)
        except Exception as exc:
            out("HUD inspect error", repr(exc))
        for target, args in (
            (unreal.UMGToolSet, ("GetWidgetDescription", (hud,))),
            (unreal.get_default_object(unreal.UMGToolSet), ("GetWidgetDescription", (hud,))),
            (unreal.get_default_object(unreal.UMGToolSet), ("GetWidgets", (hud,))),
        ):
            try:
                out(f"call_method {target} {args[0]}", target.call_method(*args))
            except Exception as exc:
                out(f"call_method error {target} {args[0]}", repr(exc))

for cls_name in (
    "CanvasPanel", "TextBlock", "Image", "Border", "Overlay", "VerticalBox",
    "ActorComponent", "StaticMeshComponent", "WidgetBlueprint", "ObjectTools",
):
    value = getattr(unreal, cls_name, None)
    out(cls_name, value)
    if value and cls_name in ("TextBlock", "CanvasPanel", "Image"):
        out(cls_name + " methods", [x for x in dir(value) if x.startswith("set_") or x.startswith("get_")][:100])

unreal.log("[T04Inspect] INSPECTION COMPLETE")

character = assets.load_asset("/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter")
if character:
    character_cdo = unreal.get_default_object(character.generated_class())
    out("Character components", [(c.get_name(), c.get_class().get_name()) for c in ActorTools.get_components(character_cdo)])
    event_graph = unreal.BlueprintEditorLibrary.find_event_graph(character)
    for search in ("BPC_Wallet", "Wallet", "钱包"):
        candidates = BlueprintTools.find_node_types(event_graph, search)
        out(f"Character node types {search}", candidates[:100])
        for candidate in candidates[:30]:
            try:
                info = BlueprintTools.get_node_type_pins(event_graph, candidate)
                out(
                    f"Node pins {candidate}",
                    ([(p.name, p.type_id) for p in info.input_pins], [(p.name, p.type_id) for p in info.output_pins]),
                )
            except Exception as exc:
                out(f"Node pins error {candidate}", repr(exc))
    try:
        array_info = BlueprintTools.get_node_type_pins(event_graph, "工具|数组|Get（复制）")
        out(
            "Array Get exact pins",
            ([(p.name, p.type_id) for p in array_info.input_pins],
             [(p.name, p.type_id) for p in array_info.output_pins]),
        )
    except Exception as exc:
        out("Array Get exact pins error", repr(exc))
