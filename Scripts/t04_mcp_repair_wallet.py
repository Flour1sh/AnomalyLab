"""Run only through the MCP ProgrammaticToolset; does not rebuild other assets."""
import json

BP = "editor_toolset.toolsets.blueprint.BlueprintTools."
WALLET = {"refPath": "/Game/Core/Components/BPC_Wallet.BPC_Wallet"}

def info(node):
    return execute_tool(BP+"get_node_infos", json.dumps({"nodes": [node]}))["returnValue"][0]

def create(graph, kind, x, y=0):
    return execute_tool(BP+"create_node", json.dumps({"graph": graph, "type_id": kind, "pos": {"x": x, "y": y}}))["returnValue"]

def pin(node, name, output=False):
    values = info(node)["output_pins" if output else "input_pins"]
    matches = [p["pin_id"] for p in values if p["name"] == name]
    assert len(matches) == 1, (name, values)
    return matches[0]

def connect(a, ap, b, bp):
    return execute_tool(BP+"connect_pins", json.dumps({"output_pin": pin(a, ap, True), "input_pin": pin(b, bp)}))

def value(node, name, val):
    return execute_tool(BP+"set_pin_value", json.dumps({"pin": pin(node, name), "value": val}))

def graph(name, params):
    g = execute_tool(BP+"add_function_graph", json.dumps({"blueprint": WALLET, "graph_name": name}))["returnValue"]
    assert g["refPath"].endswith(":"+name), g
    for pname, is_input in params:
        execute_tool(BP+"add_function_param", json.dumps({"graph": g, "param_name": pname, "param_type": "int", "input_param": is_input}))
    return g

def nodes(g):
    return execute_tool(BP+"find_nodes", json.dumps({"graph": g, "title": ""}))["returnValue"]

def compile_wallet():
    return execute_tool(BP+"compile_blueprint", json.dumps({"blueprint": WALLET, "warnings_as_errors": True}))

def run():
    progress = []
    try:
        g = graph("AddMoney", [("Amount", True)])
        entry = next(n for n in nodes(g) if "FunctionEntry" in n["refPath"])
        current = create(g, "变量|默认|获取Money", -650, 180)
        add = create(g, "工具|运算符|添加", -400, 180)
        setter = create(g, "变量|默认|设置Money", -100)
        connect(current, "Money", add, "A")
        connect(entry, "Amount", add, "B")
        connect(entry, "then", setter, "execute")
        connect(add, "ReturnValue", setter, "Money")
        formatter = create(g, "工具|文本|格式化文本", 150, 200)
        value(formatter, "Format", "[Wallet] Delta={Delta} NewMoney={NewMoney}")
        connect(entry, "Amount", formatter, "Delta")
        connect(setter, "Output_Get", formatter, "NewMoney")
        printer = create(g, "开发|PrintString", 500)
        value(printer, "bPrintToScreen", "false")
        value(printer, "bPrintToLog", "true")
        connect(formatter, "Result", printer, "InString")
        connect(setter, "then", printer, "execute")
        dispatch = create(g, "默认|CallOnMoneyChanged", 850)
        connect(printer, "then", dispatch, "execute")
        connect(setter, "Output_Get", dispatch, "NewMoney")
        connect(entry, "Amount", dispatch, "Delta")
        progress.append({"AddMoney": info(add)})
        g = graph("GetMoney", [("MoneyValue", False)])
        found = nodes(g)
        entry = next(n for n in found if "FunctionEntry" in n["refPath"])
        result = next(n for n in found if "FunctionResult" in n["refPath"])
        current = create(g, "变量|默认|获取Money", -250, 150)
        connect(entry, "then", result, "execute")
        connect(current, "Money", result, "MoneyValue")
        progress.append("GetMoney execution connected")
        g = graph("ResetMoney", [])
        entry = next(n for n in nodes(g) if "FunctionEntry" in n["refPath"])
        setter = create(g, "变量|默认|设置Money", 0)
        value(setter, "Money", "0")
        dispatch = create(g, "默认|CallOnMoneyChanged", 300)
        connect(entry, "then", setter, "execute")
        connect(setter, "then", dispatch, "execute")
        value(dispatch, "NewMoney", "0")
        value(dispatch, "Delta", "0")
        compile_wallet()
        progress.append("Wallet compiled; old functions retained until callers are migrated")
        return {"ok": True, "progress": progress}
    except Exception as exc:
        return {"ok": False, "progress": progress, "error": str(exc)}
