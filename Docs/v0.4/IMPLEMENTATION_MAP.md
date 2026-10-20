# Actual implementation map

当前T27–T31扩展映射见文末；初始化段落保留基线审计时间，不代表当前没有Meta/商店。

2026-10-12 / Asia/Shanghai。工作工程 `F:/AnomalyLab/我的项目3`；无 Git。基线 `RC_20261011T225958`，验收归档 `Saved/Releases/v0.3_ScenePolish_Accepted_20261011/`。

## 已核实调用链

| 入口 | 权威实现（Source/AnomalyLab/ 下） | 实际资产 / 结果 |
|---|---|---|
| 默认菜单 StartButton | Private/AnomalyMenuGameMode.cpp、AnomalyMainMenuWidget.cpp | /Game/Prototype/Maps/L_MainMenu → L_Prototype；UIOnly → GameOnly |
| 地图 BeginPlay | Private/AnomalyRoundCoordinator.cpp::BeginPlay → SpawnInitialBox → SpawnNextBox | /Game/Anomalies/Containers/BP_BoxSpawner 地图实例；BoxPointLeft/Middle/Right |
| 箱初始化 | Private/AnomalyBoxActor.cpp::InitializeDefinition | /Game/Anomalies/Containers/BP_AnomalyBox；Definitions 引用 /Game/Prototype/Data/Boxes/DA_Box_* 六资产；运行时复制定义 |
| E 开箱 | /Game/Core/Components/BPC_Interaction → BPI_Interactable → NativeInteract → ValidateBoxInteraction → TryLockSelection | 相机 Visibility 300 cm；选一锁二；RevealTimer → ResolveOutcome → HandleNativeOutcome |
| Q 扫描 | Private/AnomalyScannerComponent.cpp → IAnomalyScanTarget → Box::CanScan/GetCachedReading/CompleteScan | /Game/Core/Components/BPC_Scanner、/Game/UI/WBP_ScanPanel；按 Q 1 s、300 cm；按箱/仪器缓存 |
| 装备 1/2 | Private/AnomalyEquipmentComponent.cpp | 金属价值探测仪：金额范围；生物探测仪：威胁等级；物质分析仪：高价值等级；枪无射击 |
| 实体奖励 | Coordinator::SpawnLoot → AnomalyWorldPickup.cpp → TryPickup → Inventory::TryStore | /Game/Prototype/Data/Items/DA_LabChip、DA_AnomalyCore、DA_SampleCanister、DA_SpentBattery；四格 static constexpr Capacity=4 |
| 威胁 | Coordinator::BeginThreatWarning → ActivateCurrentThreat → AnomalyThreatCharacter::ActivateThreat/StartChase/AttackTick/ResolveThreat | /Game/Anomalies/Creatures/BP_Spider；1 s 预警、330 cm/s、20 s、80 cm 水平接触、Visibility 遮挡、25 伤害/1.5 s 冷却 |
| 决策/撤离 | ContinueRun / CashOut → ReturningToExtraction → ConfirmExtraction → next-tick CommitExtraction → EndRun | 返回入口手动 E、XY 325 cm/高差 180 cm/遮挡；死亡优先；Wallet 只在成功撤离兑现 |
| 终局/重开 | EndRun / CleanupCurrentRound；BP_FirstPersonCharacter::T06Restart → GetCurrentLevelName → OpenLevel | 局内背包/箱子/威胁/计时清理；两次收容强制返程；入口不免伤 |
| HUD | Coordinator::Tick → AnomalyExplorationWidget::Present/PresentInventory/PresentDamage | /Game/UI/WBP_ExplorationPrompt；被动显示，原 HUD 仅 Exploration 隐藏 |

随机流：Coordinator 原生成使用 FMath::RandRange 等权抽三个公开型并修复全同型；Box 的 ConfigurationStream 抽 Unknown 隐藏配置，OutcomeStream 只用于开奖/金额，VisualStream 独立。扫描不使用这些随机流。六配置真实 uasset 审计输出 `Saved/V04/initialization/asset_audit.json`，与 `Scripts/t11_data.py` 对照。不存在 USaveGame/Meta/商店；Wallet 是本局展示值，不可当长期余额。

## 构建与证据

- UE 5.8：E:/UE_5.8；UBT .NET 10、UnrealEditor-Cmd 已确认存在。中文 PCH 使用 `F:/AnomalyLab/CppBuildWork/20260929T083920372566Z` ASCII 副本，`Scripts/cpp_migration.py build-editor` 部署 DLL。构建期间关闭使用该模块的 UE 进程。
- 开始时 F 余量约 285.6 GiB、E 79.9 GiB、C 25.5 GiB；UBT 限并发 2，打包 1。CIM 内存查询受限，不伪报可用内存；保留原有限并发策略。
- 后续实际 UBT 日志报告 CPU 24 物理/32 逻辑核、31.8 GB 物理内存、编译时 19.9 GB/33.8 GB committed；仍保持有限并发。
- 核心脚本 run_v03.py（默认/菜单真实链路）、run_t18.py（Legacy stats/decision/flow）、verify_v03_assets.py（重载）、package_v03.py（仅历史 v0.3，不用它覆盖新版本报告）。
- 初始化快照 `Saved/V04/Checkpoint_20261012T074812_initialization/`，1,279 文件哈希校验通过；新快照脚本 checkpoint_v04.py。v0.3 归档校验清单 1,869 文件通过；旧验证命令更新派生报告一事已记录 KNOWN_ISSUES。
- 初始化快照的 Source/Config/Content 共 1,124 文件与 v0.3 已验收归档清单逐项完全相同；基线不存在未记录的玩法/资产差异。

## 任务映射及边界

| 任务 | 预计最小改动位置 | 依赖/风险 |
|---|---|---|
| T26（本轮） | 新 AnomalyRegionDefinition.h/.cpp；Box 初始化/扫描日志；Coordinator 生成/区域统计/提示；ExplorationWidget 可选绑定；新增区域资产与仅 L_Prototype/HUD；原生统计与资产重载脚本 | 对共享定义先复制再修正；保留 Unknown；全同型修复按区域权重排除原型；Legacy 不使用区域路径；固定种子 Editor/包精确对照 |
| T27（未开始） | Scanner + Box 扫描缓存权威提交、HUD | T26 门槛通过；无现有电池/次数属性 |
| T28（未开始） | Coordinator 阶段门控、Inventory 容量、装备/商店配置/UI | T27；四格硬上限需明确迁移，不在 T26 改 |
| T29（未开始） | Meta SaveGame、交易提交/终局快照 | T28；不要把当前 Wallet 当永久余额；独立测试槽 |
| T30（未开始） | 新行为类 + 区域 AllowedAnomalies | T26、T27；复用伤害/终局清理，但注视判定需独立 |
| T31（未开始） | 数据配置/采样/真人记录 | T26–T30；机器人≠真人样本 |
| T32（未开始） | 全矩阵/包/只读归档验证 | 全部依赖 |

## T26 PLAN

1. 审计真实六配置/地图实例并保存 JSON；v0.3 核心/Legacy 回归通过后实施。
2. 新区域 PrimaryDataAsset：稳定 ID/中文名/描述、三公开型权重、三隐藏型权重、三结果乘数、金额乘数、扫描误差增量、允许异常（当前 Chaser）。所有非有限/负值/空支持/不可运行异常/溢出拒绝。
3. 仅 Exploration 实例启用区域规则，生成前显式配置点位→区域引用，deferred spawn 注入；初始化后复制快照。扫描读调整后的概率范围，开奖仍仅在 ResolveOutcome 发生。
4. 独立区域提示框显示“区域大体倾向”，不泄露隐藏配置/精确开奖结果；不挤占原交互提示。原中文音画/UI 保留。
5. 区域日志记录 open_count/scan_count/reward/threat/survive。扫描只计首次仪器成功；缓存复看不重复计。
6. 固定种子原生 Monte Carlo：按生产三箱抽样及修复，≥30,000 轮/区域；均值/方差/95% 区间与威胁率；同箱型/区域/seed Editor 与包完整签名相同；边界非法权重/Unknown/扫描不改变结果/锁箱/继续/返程回归。
7. 编译→新增资产→独立进程重载→统计/旧路径→新 Win64 T26 检查点包→双分辨率实景截图→进度/配置报告/快照。编译或验收失败先修复，不进入 T27。

人工键鼠/听感/取舍体验单列 Pending Human；不能把自动断言计数写成真人样本。

## T27–T31 实际扩展
| 功能 | 实际权威调用链 | 数据与表现 |
|---|---|---|
| 有限扫描 | Scanner::InitializeRunResources → Box::CompleteScan → CommitCharge → ScanCache | MaxCharges三项；WBP_ScanPanel 原树扩容，可靠性与次数分离 |
| 局外商店 | Coordinator::BeginPlay → Preparation；↑↓/Enter → PurchaseProduct → Subsystem::Purchase → Commit | DA_ProgressionConfig；WBP_ExplorationPrompt ShopText/Backing/MetaText |
| 新局装备 | StartPreparedRun → Meta::BeginRun持久消耗诱饵 → Scanner预算/精度 + Inventory容量 | 永久电池/精度/背包，一次性诱饵 |
| 诱饵 | F → UseDecoy → 落地Actor/寿命 → Threat::TryLure/GetPursuitTarget | 范围1200/5秒，Chaser可引，Observer免疫 |
| 永久经济 | EndRun封口 → CreditExtraction(RunId) → USaveGame事务写入 → EndRunSnapshot → HUD | Schema2，CRC/.tmp/.bak，隔离Automation槽；Wallet仅本局适配 |
| 观察者 | Box::SelectThreatClass独立流 → DeferredSpawn Config → Warning → Observer::Tick + base Attack/Resolve | DA_ObserverConfig + 三材质 + 低模；WBP_HealthThreat两行状态 |
| 回合曲线 | SpawnNextBox(RoundId) → Box::InitializeDefinition复制 → Region::ApplyTo → Balance::ApplyTo | DA_BalanceConfig；第1轮原样，后续小幅有界；Legacy空引用 |
| 验证 | run_v04 / run_t29 / run_t30 / run_t31 / run_t26 / run_v03 / run_t18 | 显式命令行才安装驱动；正常启动无驱动；真实渲染与人类验收独立 |
