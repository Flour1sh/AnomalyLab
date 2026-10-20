import json


def graphs(path):
    return execute_tool("editor_toolset.toolsets.blueprint.BlueprintTools.list_graphs", json.dumps({"blueprint": {"refPath": path}}))["returnValue"]

def nodes(graph):
    refs = execute_tool("editor_toolset.toolsets.blueprint.BlueprintTools.find_nodes", json.dumps({"graph": graph, "title": ""}))["returnValue"]
    return execute_tool("editor_toolset.toolsets.blueprint.BlueprintTools.get_node_infos", json.dumps({"nodes": refs}))["returnValue"]

def compact(info):
    return {"node": info["node"]["refPath"], "type": info["type_id"], "pins": [{"name": p["name"], "id": p["pin_id"]["index_id"], "dir": d, "type": p["type_id"], "value": p["value"], "links": [q["node"]["refPath"].rsplit(".",1)[-1] + ":" + str(q["index_id"]) for q in p["connected_pins"]]} for d in ("input_pins", "output_pins") for p in info[d]]}


def run():
    paths = ["/Game/Core/Components/BPC_Wallet.BPC_Wallet", "/Game/UI/WBP_PrototypeHUD.WBP_PrototypeHUD", "/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter.BP_FirstPersonCharacter"]
    selected = {paths[0]: ["AddMoney_18", "GetMoney_18"], paths[1]: ["UpdateFocus"], paths[2]: ["EventGraph", "HandleOutcomeResolved"]}
    return {g["refPath"]: [compact(n) for n in nodes(g)] for path in paths for g in graphs(path) if g["refPath"].rsplit(":",1)[-1] in selected[path]}
