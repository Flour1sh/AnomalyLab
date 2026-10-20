# T14 决策与终局构建

2026-10-05 按用户要求仅用 Python/C++ 构建；等待后续 UE MCP 与人工玩法测试。本次未启动 UE MCP 扩展、屏幕接管、PIE 或打包。

## 实现

- `AAnomalyRoundCoordinator` 在奖励展示两秒或旧威胁结算后统一清理当前三箱，增加完成回合数，并进入原生状态 `4 = PostRoundDecision`；不再自动生成下一轮。原有 0–3 状态索引仍供旧蓝图枚举适配。
- 决策阶段冻结玩家移动、取消扫描，保留鼠标观察。装备组件现有按键绑定在此状态把 `1` 路由到 `ContinueRun`、`2` 路由到 `CashOut`；其他阶段继续按原装备规则。继续保留钱包余额并生成下一组三箱；第二次成功收容后隐藏继续选项且原生接口拒绝继续。
- 撤离进入 `CashedOut` 终局；技术错误进入 `Error`。保留 `Failed` 分类供 T15 死亡接入，本阶段不实现 HP、伤害或 20 秒追逐。终局冻结金额、完成回合数、成功收容次数及从首次三箱可选开始计算的局时长。技术错误单独显示，不作成功撤离；独立的持久银行/存档仍不需要。
- `UAnomalyDecisionWidget` 被动显示简体中文决策和终局内容，Coordinator 控制可见性与数据。Python 生成 `/Game/UI/WBP_RoundDecision`，配置到现有 `BP_BoxSpawner` 并将奖励展示间隔设为 2 秒。原有 HUD 和 R 重开蓝图接口保持；终局仍向旧蓝图广播 Ended。

## 构建与证据

```powershell
python '我的项目3/Scripts/cpp_migration.py' build-editor
python '我的项目3/Scripts/cpp_migration.py' editor --script build_t14_assets.py --phase t14-build
python '我的项目3/Scripts/cpp_migration.py' editor --script verify_t14_assets.py --phase t14-reload
```

最终 Editor 编译退出码 0、UBT `Result: Succeeded`。资产生成与独立进程重载退出码均为 0；报告见 `Saved/T14/build_report.json`、`Saved/T14/reload_report.json`。原生源码与文档构建前备份见 `Saved/T14/SourceBefore_20261005/`；旧 uasset 备份路径由构建报告记录。原始进程日志在 `Saved/CppMigration/20260929T083920372566Z/`。重载检查确认三个相关蓝图编译、面板控件绑定、Spawner 面板类引用及 2 秒配置。

## 后续测试要点

1. 奖励/垃圾展示完进入决策且不会自动生箱；1 继续保留金额、生成三箱，2 撤离冻结金额并显示成功终局。
2. 决策时移动/扫描/装备切换受控但可观察；跨状态按键不误触发。终局 E/Q/1/2 不推进玩法，R 重开清零金额和统计。
3. 威胁结算后进入决策；第二次成功收容后只允许撤离。重复或过期回调不能重复计数、付款或生成。
4. 检查中文决策/终局面板与现有 HUD 是否重叠，金额、回合数、收容数、用时是否正确；技术异常应独立显示。

构建当时只证明编译、资产生成和独立重载；后续自动运行结果见下节。HP、死亡失败局及 20 秒追逐留给 T15。

## 自动运行测试（2026-10-05）

用户授权后执行 `python '我的项目3/Scripts/run_t14_smoke.py'`。最终隐藏 NullRHI 进程在真实关卡通过 47/47 项，退出码 0，且禁用 UE MCP 相关插件。检查覆盖决策、继续、撤离、两次威胁限制、金额/统计快照、异常终局及重载重置；详见 `Saved/T14/test_log.md` 与 `runtime_report.json`。该自动运行未验证实体按键、画面、音效及独立包。

## 人工验收（2026-10-05）

用户反馈：“人工验收通过”。据此将 T14 标记为人工验收通过，下一阶段为 T15 生命与追逐。此为用户总体结论，未提供逐项人工操作记录或独立包报告；既有自动测试边界保持不变。独立验收日志见 `Saved/T14/acceptance_log.md`。
