# v0.3 基线审计（T20 构建前，2026-10-11）

本轮授权：根据 v0.3 日志和总体计划推进 T20，只使用 Python/C++ 构建；不调用 UE MCP、不操作屏幕、不运行 PIE/玩法/视听测试。T19 人工待测项继续保留，不推断已通过。

实际入口：`L_MainMenu` → `/Game/Prototype/Maps/L_Prototype`（玩家名称 Level01）。`BP_FirstPersonGameMode`、Character、Controller、输入映射仍为既有 Blueprint。工程没有 Git，恢复点见 `Saved/T20/checkpoint_path.txt`，资产另行备份。

| 已有项 | 复用 / 迁移 |
|---|---|
| `BP_BoxSpawner : AAnomalyRoundCoordinator` | 复用三候选、至少两箱型、RoundId、选一锁二和完整候选生成重试；仅探索地图实例配置空间点位 |
| `BP_AnomalyBox : AAnomalyBoxActor` | 保留定义/结果独立随机流、1 秒揭晓、线索、锁定 Widget；探索模式补原生距离/遮挡检查与独立怪物偏移 |
| `BPC_Interaction` | 0.05 秒更新，E 时重新相机 Visibility 射线 300 cm，BPI 调用 NativeInteract；不新增 E 监听 |
| Scanner / Equipment | 复用 Q 一秒与三仪器缓存、取消和装备切换；不改变扫描结果语义 |
| Wallet / Health / Threat / Decision | 保留直接奖励、生命与轮次规则；实体 Loot、背包与实际撤离兑现留 T21–T23 |
| 旧实验室 | 导出 44 个场景 Actor 与交互图，见 `Saved/T20/baseline_inspection.json`；现有低模道具为带世界偏移的网格，放置时按包围盒中心归位 |
| LegacyPrototype | 默认原生模式仍为 LegacyPrototype；生成独立旧地图副本，供后续回归，不覆盖旧资产包原件 |

风险：旧三点仅间隔 220 cm，旧房间 1600×2000 cm；不能直接平移箱子穿过旧墙。旧怪物偏移 (250,-300,-3) 在新布局可能出墙，探索模式需单独配置。旧决策冻结移动，探索模式在决策阶段保留行走以允许返回入口，终局仍冻结。导航覆盖、碰撞、中文布局及真实按键均须后续可见验收。

本阶段迁移原地图空间与实例设置，不改菜单、箱型概率、金额、威胁时长或二次收容终止规则。所有源码/资产构建结果与玩法验收分列记录。
