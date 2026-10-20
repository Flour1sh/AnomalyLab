import json

def types(graph, query):
    return execute_tool("editor_toolset.toolsets.blueprint.BlueprintTools.find_node_types", json.dumps({"graph": {"refPath": graph}, "type_id_filter": query, "context_pins": []}))["returnValue"]

def props(path):
    return execute_tool("editor_toolset.toolsets.object.ObjectTools.list_properties", json.dumps({"instance": {"refPath": path}}))["returnValue"]

def functions(path):
    return execute_tool("editor_toolset.toolsets.blueprint.BlueprintTools.list_functions", json.dumps({"blueprint": {"refPath": path}}))["returnValue"]

def run():
    wallet = "/Game/Core/Components/BPC_Wallet.BPC_Wallet"
    char = "/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter.BP_FirstPersonCharacter"
    hud = "/Game/UI/WBP_PrototypeHUD.WBP_PrototypeHUD"
    result = {"types": {q: types(char+":EventGraph", q) for q in ("GetActorOfClass", "UpdateMoney", "GetMoney", "获取PrototypeHUD")}}
    selected = [(char, "HandleMoneyChanged_6"), (char, "HandleFocusChanged_6"), (hud, "UpdateMoney"), ("/Game/Anomalies/Containers/BP_AnomalyBox.BP_AnomalyBox", "EventGraph")]
    for path, name in selected:
        refs = execute_tool("editor_toolset.toolsets.blueprint.BlueprintTools.find_nodes", json.dumps({"graph": {"refPath": path+":"+name}, "title": ""}))["returnValue"]
        infos = execute_tool("editor_toolset.toolsets.blueprint.BlueprintTools.get_node_infos", json.dumps({"nodes": refs}))["returnValue"]
        result[name] = [i for i in infos if name != "EventGraph" or "AddMoney" in i["type_id"]]
    return result
