def run():
    g = graph(HUD, "EventGraph")
    result = []
    for n in infos(nodes(g)):
        inputs = [p for p in n["input_pins"] if p["name"] in ("Duration", "InOpacity", "execute")]
        result.append({"node": n["node"], "type": n["type_id"], "inputs": inputs})
    return {"hud_animation": result, "graph_names": {bp["refPath"]: [g["refPath"].rsplit(":",1)[-1] for g in graphs(bp)] for bp in (WALLET, HUD, CHAR)}}
