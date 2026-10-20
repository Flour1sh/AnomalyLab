# T15 生命与追逐构建

2026-10-05 按用户要求仅用 Python/C++ 构建；UE MCP 扩展、屏幕接管、PIE、玩法测试和打包留待后续。

## 实现

- `UAnomalyHealthComponent` 是玩家 HP 唯一可信来源：100/100 起始、威胁每次 25 伤害、全局受伤间隔至少 1.5 秒。HP 跨轮保留，不自动回血；每局通过关卡重载重置。组件只在有效追逐期接受伤害，重复或迟到伤害被拒绝；死亡委托只触发一次。
- `AAnomalyThreatCharacter` 生成时静止。Coordinator 显示 1 秒“危险：收容失效”后激活，移动初值 330 cm/s，追逐 20 秒。威胁每 0.1 秒检查玩家是否在水平 80 cm、竖直 120 cm 内；持续接触和再次进入共用 Health 的 1.5 秒冷却。成功到时关闭伤害并显示 1 秒“收容完成”，然后才计入一次成功收容并进入 T14 决策。
- 玩家死亡优先进入 `Failed` 终局，取消预警、追逐展示与回合计时器并清理怪物、候选箱和结果。先保存损失金额快照，再通过 Wallet 接口清零；本次带出为 $0。死亡不能同时算成功收容或再生成三箱。
- 怪物生成失败不再由旧三秒 fallback 假装成功；最多每秒重试三次，仍失败则进入单独技术异常。怪物 `MaxHealth` 仅作未来战斗配置，不实现受击或射击。
- Python 生成 `/Game/Core/Components/BPC_Health`、`/Game/UI/WBP_HealthThreat`，将 Health 组件挂到玩家，并保存 `BP_Spider`、`BP_BoxSpawner` 的 T15 默认值。状态面板显示 HP、预警/倒计时/收容、受伤提示；尚未进行可见画面检查。

## 构建与证据

```powershell
python '我的项目3/Scripts/cpp_migration.py' build-editor
python '我的项目3/Scripts/cpp_migration.py' editor --script build_t15_assets.py --phase t15-build
python '我的项目3/Scripts/cpp_migration.py' editor --script verify_t15_assets.py --phase t15-reload
```

最终 Editor 编译退出码 0，UBT `Result: Succeeded`；资产生成及独立进程重载均退出码 0。见 `Saved/T15/build_report.json`、`reload_report.json`。源码/文档修改前备份在 `Saved/T15/SourceBefore_20261005/`，旧 uasset 备份由构建报告给出。原始编译与资产进程日志在 `Saved/CppMigration/20260929T083920372566Z/`。重载核对唯一玩家 Health 组件、HP/伤害/冷却/面板类、Spider 速度与 20 秒时长、Spawner 预警与重试配置、三个状态控件及五个蓝图编译。

## 后续 UE MCP/人工测试

1. 可见场景检查预警完整 1 秒后才移动/受伤，怪物能从被选箱附近追逐并绕障；20 秒后消失、显示收容完成 1 秒、只计数一次并进入决策。
2. 持续接触连续四次 25 伤害能致死，间隔不少于 1.5 秒；离开再进入不重置冷却。检查 HP 100→75→50→25→0、红色受伤反馈及 HP 跨轮保留。
3. 致死时失去本局未带出金额，终局“行动失败/损失金额/本次带出 $0”正确；旧存活计时与迟到攻击不能继续结算、伤害或生箱。R 重开恢复 100 HP、$0 和三箱。
4. 技术异常专项：怪物生成失败重试上限及 Error 终局；导航失败必须记录并实景检查，不能仅凭倒计时通过断言追逐正常。
5. 1920×1080 与 1280×720 检查中文、HP/倒计时/受伤提示与既有 HUD 的遮挡；实体输入和独立包尚未验证。

本轮只证明源码编译、资产生成与独立重载；不记录以上玩法和画面检查为已通过。历史 `AnomalyMigrationSmoke` 和 `AnomalyT14Smoke` 按旧时长编写，不用它们判断 T15 行为。

## 2026-10-06 自动测试续记

用户随后授权自动完成 v0.2 剩余流程。新增 `run_t15_smoke.py` 在真实地图隐藏 NullRHI 中完成 T15 的 20 秒追逐、持续接触致死、收容与死亡互斥以及怪物生成失败重试。最终 5,162/5,162 通过，原始失败尝试、修正原因和限制见 `Saved/T15/test_log.md`。这更新了上文“玩法待测”的构建时状态，但仍未进行可见画面/实体输入人工验收。T16–T18 与独立包后续验证见 `Saved/T16/`、`Saved/T17/`、`Saved/T18/test_log.md`。
