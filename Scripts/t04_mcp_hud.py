def break_wire(output_pin, input_pin):
    execute_tool(BP+"break_pins", json.dumps({"output_pin": output_pin, "input_pin": input_pin}))

def run():
    g = graph(HUD, "ShowOutcome")
    original = infos(nodes(g))
    assert not any("SetColorandOpacity" in n["type_id"] for n in original), "Colors already patched; inspect before retrying"
    colored = []
    for n in original:
        if "SetText" not in n["type_id"]:
            continue
        text = next(p["value"] for p in n["input_pins"] if p["name"] == "InText")
        if "HIGH VALUE" in text:
            rgb = (1.0, 0.72, 0.08)
        elif "TRASH" in text:
            rgb = (0.55, 0.55, 0.55)
        elif "WARNING" in text:
            rgb = (1.0, 0.08, 0.05)
        else:
            raise ValueError(text)
        color = create(g, "外观|SetColorandOpacity", n["position"]["x"]+220, n["position"]["y"], {"refPath": "/Script/UMG.TextBlock"})
        color_info = info(color)
        color_pin = next(p["name"] for p in color_info["input_pins"] if "Color" in p["name"])
        value(color, color_pin, "(SpecifiedColor=(R="+str(rgb[0])+",G="+str(rgb[1])+",B="+str(rgb[2])+",A=1.0),ColorUseRule=UseColor_Specified)")
        target = next(p["connected_pins"][0] for p in n["input_pins"] if p["name"] == "self")
        wire(target, pin(color, "self"))
        out = next(p for p in n["output_pins"] if p["name"] == "then")
        for downstream in out["connected_pins"]:
            break_wire(out["pin_id"], downstream)
            wire(pin(color, "then", True), downstream)
        wire(out["pin_id"], pin(color, "execute"))
        colored.append(text)
    assert len(colored) == 3

    # Preserve the existing fade-in and hold; extend four fade-out steps to .25 s.
    event = graph(HUD, "EventGraph")
    all_nodes = infos(nodes(event))
    by_path = {n["node"]["refPath"]: n for n in all_nodes}
    fades = []
    for n in all_nodes:
        if not n["type_id"].lower().endswith("|delay") and not n["type_id"].endswith("|延迟"):
            continue
        predecessors = [p for p in n["input_pins"] if p["name"] == "execute"]
        if not predecessors or not predecessors[0]["connected_pins"]:
            continue
        predecessor = by_path[predecessors[0]["connected_pins"][0]["node"]["refPath"]]
        opacity = [p for p in predecessor["input_pins"] if p["name"] == "InOpacity"]
        if opacity and round(float(opacity[0]["value"]), 2) in (0.8, 0.6, 0.4, 0.2):
            value(n["node"], "Duration", "0.0625")
            fades.append(opacity[0]["value"])
    assert len(fades) == 4, fades

    g = graph(HUD, "UpdateFocus")
    found = infos(nodes(g))
    entry = next(n["node"] for n in found if "FunctionEntry" in n["node"]["refPath"])
    first_branch = next(n["node"] for n in found if "IfThenElse" in n["node"]["refPath"])
    show = next(n["node"] for n in found if any(p["name"] == "InVisibility" and p["value"] == "Visible" for p in n["input_pins"]))
    hide = next(n["node"] for n in found if any(p["name"] == "InVisibility" and p["value"] == "Collapsed" for p in n["input_pins"]))
    cast = create(g, exact_type(g, "CastToBP_AnomalyBox"), -50, -100)
    break_wire(pin(first_branch, "then", True), pin(show, "execute"))
    connect(first_branch, "then", cast, "execute")
    connect(entry, "FocusedActor", cast, "Object")
    connect(cast, "CastFailed", hide, "execute")
    cast_result = next(p["name"] for p in info(cast)["output_pins"] if p["name"].startswith("As"))
    opened_type = exact_type(g, "获取Opened", [pin(cast, cast_result, True)])
    # Contextual variable menus use a different category; use its declared owner.
    opened = create(g, "类|BPAnomalyBox|获取Opened", 250, 200)
    connect(cast, cast_result, opened, "self")
    check = create(g, "工具|流程控制|分支", 500, -100)
    connect(cast, "then", check, "execute")
    connect(opened, "bOpened", check, "Condition")
    connect(check, "then", hide, "execute")
    connect(check, "else", show, "execute")
    assert execute_tool("UMGToolSet.UMGToolSet.CompileWidgetBlueprint", json.dumps({"widgetBlueprint": HUD}))["returnValue"]
    compile_bp(CHAR)
    save([HUD, CHAR])
    return {"ok": True, "colors": colored, "fade_out_steps": fades, "animation_total_seconds": 1.75, "focus": "valid unopened BP_AnomalyBox only", "saved": True}
