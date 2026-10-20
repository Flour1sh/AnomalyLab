def run():
    progress = []
    try:
        keep = {"HandleMoneyChanged_6", "HandleFocusChanged_6", "HandleOutcomeResolved"}
        removed = []
        for g in graphs(CHAR):
            name = g["refPath"].rsplit(":", 1)[-1]
            if name.startswith(("HandleMoneyChanged", "HandleFocusChanged", "HandleOutcomeResolved")) and name not in keep:
                remove_graph(CHAR, name)
                removed.append(name)
        progress.append({"removed_old_character_functions": removed})
        g = graph(CHAR, "HandleMoneyChanged_6")
        for n in infos(nodes(g)):
            if n["type_id"].rsplit("|", 1)[-1].startswith("UpdateMoney_"):
                context = next(p["connected_pins"] for p in n["input_pins"] if p["name"] == "self")
                replace_call(g, n["node"], "类|WBPPrototypeHUD|UpdateMoney")
        progress.append("Money callback migrated to canonical HUD UpdateMoney")
        g = graph(BOX, "EventGraph")
        count = 0
        for n in infos(nodes(g)):
            if n["type_id"].rsplit("|", 1)[-1].startswith("AddMoney_"):
                context = next(p["connected_pins"] for p in n["input_pins"] if p["name"] == "self")
                replace_call(g, n["node"], "类|BPCWallet|AddMoney")
                count += 1
        assert count == 4, count
        progress.append({"box_reward_calls_migrated": count})
        removed = []
        for g in graphs(WALLET):
            name = g["refPath"].rsplit(":", 1)[-1]
            if name.startswith(("AddMoney_", "GetMoney_", "ResetMoney_")):
                remove_graph(WALLET, name)
                removed.append(name)
        progress.append({"removed_wallet_duplicates": len(removed)})
        for g in graphs(HUD):
            name = g["refPath"].rsplit(":", 1)[-1]
            if name in ("UpdateMoney_0", "UpdateMoney_1"):
                remove_graph(HUD, name)
        for bp in (WALLET, HUD, BOX, CHAR):
            compile_bp(bp)
        save([WALLET, HUD, BOX, CHAR])
        progress.append("All four assets compiled and saved; Character initialization still pending")
        return {"ok": True, "progress": progress}
    except Exception as exc:
        return {"ok": False, "progress": progress, "error": str(exc)}
