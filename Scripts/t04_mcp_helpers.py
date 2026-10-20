import json

BP = "editor_toolset.toolsets.blueprint.BlueprintTools."
WALLET = {"refPath": "/Game/Core/Components/BPC_Wallet.BPC_Wallet"}
CHAR = {"refPath": "/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter.BP_FirstPersonCharacter"}
HUD = {"refPath": "/Game/UI/WBP_PrototypeHUD.WBP_PrototypeHUD"}
BOX = {"refPath": "/Game/Anomalies/Containers/BP_AnomalyBox.BP_AnomalyBox"}

def infos(nodes):
    return execute_tool(BP+"get_node_infos", json.dumps({"nodes": nodes}))["returnValue"]

def info(node):
    return infos([node])[0]

def graphs(bp):
    return execute_tool(BP+"list_graphs", json.dumps({"blueprint": bp}))["returnValue"]

def nodes(graph):
    return execute_tool(BP+"find_nodes", json.dumps({"graph": graph, "title": ""}))["returnValue"]

def graph(bp, name):
    return next(g for g in graphs(bp) if g["refPath"].endswith(":"+name))

def create(g, kind, x=0, y=0, owner=None):
    args = {"graph": g, "type_id": kind, "pos": {"x": x, "y": y}}
    if owner is not None:
        args["declaring_class"] = owner
    return execute_tool(BP+"create_node", json.dumps(args))["returnValue"]

def pin(node, name, output=False):
    values = info(node)["output_pins" if output else "input_pins"]
    matches = [p["pin_id"] for p in values if p["name"] == name]
    assert len(matches) == 1, (node, name, [p["name"] for p in values])
    return matches[0]

def wire(output_pin, input_pin):
    execute_tool(BP+"connect_pins", json.dumps({"output_pin": output_pin, "input_pin": input_pin}))

def connect(a, ap, b, bp):
    wire(pin(a, ap, True), pin(b, bp))

def value(node, name, val):
    execute_tool(BP+"set_pin_value", json.dumps({"pin": pin(node, name), "value": val}))

def types(g, query, context=None):
    return execute_tool(BP+"find_node_types", json.dumps({"graph": g, "type_id_filter": query, "context_pins": [] if context is None else context}))["returnValue"]

def exact_type(g, name, context=None):
    found = types(g, name, context)
    matches = list(dict.fromkeys(v for v in found if v.rsplit("|", 1)[-1].lower() == name.lower()))
    assert len(matches) == 1, (name, matches, found)
    return matches[0]

def compile_bp(bp):
    execute_tool(BP+"compile_blueprint", json.dumps({"blueprint": bp, "warnings_as_errors": True}))

def remove_graph(bp, name):
    execute_tool(BP+"remove_function_graph", json.dumps({"blueprint": bp, "graph_name": name}))

def delete(node):
    execute_tool(BP+"delete_node", json.dumps({"node": node}))

def save(bps):
    ok = execute_tool("editor_toolset.toolsets.asset.AssetTools.save_assets", json.dumps({"asset_paths": [b["refPath"] for b in bps]}))["returnValue"]
    assert ok

def replace_call(g, old, new_type):
    old_info = info(old)
    new = create(g, new_type, old_info["position"]["x"], old_info["position"]["y"])
    for field, out in (("input_pins", False), ("output_pins", True)):
        for p in old_info[field]:
            target = pin(new, p["name"], out)
            for other in p["connected_pins"]:
                wire(target, other) if out else wire(other, target)
            if not out and not p["connected_pins"] and p["value"]:
                value(new, p["name"], p["value"])
    delete(old)
    return new
