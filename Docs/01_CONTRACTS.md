# ANOMALY LAB PROTOTYPE — STABLE CONTRACTS

## v0.4 T29 持久化 / 终局（2026-10-12）

- Meta 使用 UAnomalyMetaSaveGame + 长度/CRC envelope，SchemaVersion=2；1 迁移合法化；更高版本保留原字节并阻止提交。无档 0，无效主档优先验证备份，否则默认；坏主档保留诊断副本并日志。
- 唯一 Commit 先序列化临时档/读回验证、保留旧有效备份、替换主档并验证，再变更内存。购买失败不扣费/授予；BeginRun 消耗预存诱饵也需保存成功才入局。失败可在整备检查磁盘/权限后重试。
- 只有已封闭 NativeState=3、成功物理入口授权的 RunId 可 CreditExtraction。最近 128 结算/购买 Guid 与 Revision 保存；重复输入/回调不增加收入。保存失败结算转 Error，Carry 清理、Wallet 本局收入 0、旧 Meta 保留。
- EndSnapshot 为私有、只读返回的 FAnomalyEndRunSnapshot，封闭终局后只赋值一次；包含 reason/carry兑现或损失/永久余额/回合/收容/时间/物品文本/持久提交标识，终局 Widget 读取该快照。
- 默认槽 AnomalyLab_Meta_v04，位置 FPaths::ProjectSavedDir()/SaveGames；打包版本实际路径见 [MetaSave] 日志。-AnomalySaveSlot 可指定安全档名；已知测试开关强制 Automation_ 前缀或自动唯一测试槽。脚本清理只匹配自己的 Automation_<unique>.sav*。
- 死亡/Error/回菜单/强退不新增收入，已兑现货币与永久升级保留；不保存局内扫描余量、HP、世界物品或 Carry。R 返回新整备阶段。

## v0.4 T28 整备 / 装备（2026-10-12）

- L_Prototype 显式启用 bUsePreparation + DA_ProgressionConfig；BeginPlay 先进入追加枚举 Preparation，原 NativeState/旧枚举索引保持。无箱子/威胁，移动暂停；E 由原生 StartPreparedRun 开局。局内入口不增加无敌或购物能力。
- UAnomalyProgressionSubsystem 是内存 Meta 权威，起始 0；未把旧 Wallet 当永久币。唯一成功入口结算增加 Meta（T29 持久化），Wallet 仍为本局结算适配值，Carry 为未兑现物品。
- Purchase 校验调用者当前整备权限、商品、余额/上限、请求 Guid、ExpectedRevision；成功才改状态。Coordinator 同帧仅接受一笔成功购买；UI 仅显示文本。四项价格/上限/效果来自 DataAsset。
- 新局三仪器各 +BatteryLevel×ChargesPerLevel；PrecisionReduction 有限缩窄金额区间扩展和概率等级误差，不消费结果 RNG、不保证开奖结果。缓存保持该次读取结果。
- Inventory.GetCapacity 当前 4 或 5；Capacity 常量仅为旧兼容默认，不再用于运行时满格判断。
- 预存诱饵在 BeginRun 原子转入 DecoysRemaining 并清空预存；局内 F 生成有限寿命实体来源、消耗一个，范围内可诱导威胁改 MoveTo 目标，到期恢复玩家。死亡/终局销毁来源；观察者将在 T30 明确免疫。

## v0.4 T27 扫描资源契约（2026-10-12）

- ScannerComponent 每局维护 Metal/Bio/Matter 独立预算；MaxCharges 默认 [3,3,3]，合法化至 0–20。Legacy 不扣费。
- Box.CompleteScan 先复核 CanScan/仪器，再读取缓存；新读数全部构造成功后，游戏线程 CommitCharge → ScanCache.Add → region telemetry，无事件插入提交中途。零资源不写缓存；重复完成/同箱缓存复看免费；过期/锁定箱连缓存也拒绝。
- Q 一秒/3 米/Visibility 与取消规则保持；取消不调用 CommitCharge。新局组件初始化或整备开始时初始化资源；ContinueRun 不初始化。容量加成由新局权威入口应用。
- HUD 明确分开“扫描剩余”和“可靠性”。资源可耗尽，但 E 开箱继续可用；缓存不消费 Outcome RNG。

## v0.4 T26 区域契约（2026-10-12，用户总体验收通过）

- 仅 Exploration 且 `bUseRegionRules=true` 时启用；`RegionRules` 按 BoxPointLeft/Middle/Right 显式引用三份区域资产。区域 ID 来自资产，禁止按颜色/展示文本判断。Legacy 原采样路径保持。
- `UAnomalyRegionDefinition` 定义公开/隐藏型权重、结果乘数、金额乘数、ScanErrorAdd 与 AllowedAnomalies。三项权重有限非负、公开支持至少两型；空概率质量/溢出/无效异常拒绝并 Error，不能静默回落到同质箱。T26 仅允许既有 Chaser。
- 三公开型按区域独立抽样，全同型时随机选一槽按其区域权重排除原型重抽；仍完整三箱才可选。Unknown 仅初始化抽隐藏配置，OutcomeStream 仅开奖/金额时消费，扫描不预抽。
- BeginPlay 复制区域为本局快照；Box 初始化再复制自身区域与基础定义，先验证基础数据再应用修正/归一化，绝不改共享六定义。外观线索概率与旧扫描金额扩展不改。
- `bUseFixedRegionSeed` 默认关闭；仅临时测试开启时区域采样和各箱配置/开奖种子完全可复现。区域采样/隐藏配置/开奖/视觉分流，缓存复看不消费开奖随机数。
- RegionText 只显示区域名称/公开风险收益提示；HUD 不显示隐藏配置或精确开奖结果，不接管输入。
- `[Region] id=... round=... event=... open_count/scan_count/reward/threat/survive` 为本局只读遥测。open 一次、scan 每箱每仪器首次一次、reward 为生成物品面值（不是 Wallet/提现）、threat 为开奖次数、survive 为当前威胁有效收容次数；重复/迟到回调仍由原权威入口过滤。
- event 是 FName，Editor/包的大小写可能不同（例如 threat/Threat），统计时按不区分大小写归类；计数与区域 ID 来自同一权威上下文。
- 核心背包/物理入口 E/死亡优先/两次收容强制返程/重新加载契约继续生效。T27 扫描次数和 T29 长期经济均未实现。

下文 v0.3 与更早章节按日期保留；旧章节中自动下一轮、直接 Wallet、三秒追逐等仅为历史，不覆盖最新权威接口。

## v0.3 T20 探索构建契约（2026-10-11，玩法待验收）

- Coordinator 的 `EAnomalyPlayMode` 默认 LegacyPrototype；`L_Prototype` 地图实例指定 Exploration，旧场景 `L_LegacyPrototype` 保留旧三点。点位由 BoxPointLeft/Middle/Right 组件保存，不改抽样和选一锁二。
- E 输入仍只经 BPC_Interaction → BPI → NativeInteract。Exploration 模式在 TryLockSelection 前复核 Interactor 为本地玩家、相机 Visibility 命中本箱且距离不超过 300 cm；旧模式保留原路由语义。无额外 E 按键监听。
- `WBP_ExplorationPrompt` 被动接收 Focus/Objective；不持有玩法权威。提示层在终局隐藏、EndPlay 移除。探索决策阶段允许行走，Continue/CashOut 的阶段/威胁次数门控保持；终局仍冻结。
- 怪物偏移仅对探索生成的 Box 实例生效 `(0,-300,-3)`，旧 LootSpawnPoint/CreatureSpawnPoint 保留。Box 的一次结果流、金额流和扫描缓存不变。
- R 的原 Ended 门控保留，执行链先 GetCurrentLevelName（去除编辑器前缀）再 OpenLevel。原生回归驱动同样重载当前地图，旧 Editor 回归脚本默认 Legacy。新增 Cook 地图仅保留旧模式供未来回归，本轮不打包、不跑测试。
- 入口/返回区不是免伤或物理提现功能；T20 仍为旧直接 Wallet 奖励、按 2 撤离。T21–T23 尚未实现。
- Python 构建函数仅允许非游戏 World：同步完成地图加载后生成导航，要求有效 tile > 0；不将资产检查当作运行时可达性/真实输入证明。实现与待测见 `Docs/v0.3/T20_EXPLORATION.md`。

## v0.3 T19 主菜单与关卡入口（2026-10-10）

`L_MainMenu` 单独使用 `AAnomalyMenuGameMode` 和 `AAnomalyMenuPlayerController`，无默认 Pawn/HUD。Controller 仅在本菜单创建 `WBP_MainMenu : UAnomalyMainMenuWidget`，使用 UIOnly 输入并显示鼠标。布局/颜色/中文在蓝图，原生命令只负责菜单状态、输入和设置应用。菜单没有 Coordinator，不参与三箱或经济状态。

`StartLevel01()` 只接受菜单中的一次开始请求，验证原玩法包存在，显示加载并在 0.25 秒后 `OpenLevel(/Game/Prototype/Maps/L_Prototype)`；切图时恢复 GameOnly/隐藏鼠标，菜单 EndPlay 移除 Widget/清理定时器。新地图继续使用原 Blueprint GameMode/Controller/Character；R 继续重开本关。

Settings / Guide / Quit / Loading 面板互斥，非主菜单阶段拒绝开始及主菜单命令。键盘由焦点 Widget 路由；退出确认默认选中取消。显示设置先保存草稿，只有 Apply 才经 `UGameUserSettings` 应用/确认/保存，返回不提交草稿。

Level01 PlayerStart 原 Pitch -90 / Yaw 0 已修正为 Pitch 0 / Yaw -90，解决初次进入看向地面。其他玩法权威接口与规则不变。可选 `-AnomalyMenuSmoke` 仅非 Shipping、显式参数下启用，正常启动不注入测试。详见 `Docs/v0.3/T19_MAIN_MENU.md`。

## T15 生命与追逐（2026-10-05 构建，待玩法验收）

`UAnomalyHealthComponent` 是玩家 HP 唯一来源，默认 100/100，威胁伤害 25，受伤冷却 1.5 秒，跨轮不恢复。仅由协调器在有效追逐期启用伤害；死亡委托防重复。`BPC_Health` 挂于玩家，`WBP_HealthThreat : UAnomalyStatusWidget` 被动显示 HP、预警、20 秒倒计时、收容与受伤反馈。T15 原生 `RunEndReason::Failed` 在死亡时冻结损失金额，用 Wallet 接口清零，终局本次带出 $0；清理使旧攻击与威胁计时不能再推进回合。

`AAnomalyThreatCharacter` 生成时静止，协调器在 1 秒预警后调用 `ActivateThreat()`；起始移速 330 cm/s，20 秒到期调用 `ResolveThreat()`。每 0.1 秒仅在玩家水平 80 cm、竖直 120 cm 范围内尝试伤害，Health 统一执行冷却；离开再进入不会重置冷却。存活成功立即关闭伤害并显示 1 秒“收容完成”，随后计一次收容并进入 T14 决策。怪物生成失败最多按 1 秒间隔重试三次，耗尽进入 Error，不再走旧三秒成功 fallback。怪物 `MaxHealth` 只供未来战斗配置，目前没有受击逻辑。

T15 源码和资产已编译、独立重载；实体输入、实际追逐、倒计时临界、画面及独立包尚待后续验证。旧文中“3 秒自动解决”“接触只通知一次”的描述仅代表 T15 前版本。构建与待测清单见 `Scripts/RUN_T15.md`。

## T14 决策与终局（2026-10-05 构建、自动运行及用户人工验收通过）

`AAnomalyRoundCoordinator` 原生状态索引扩展为 `4 = PostRoundDecision`；旧蓝图 `EPrototypeRoundState` 仍只镜像 0–3，决策以 `IsDecisionActive()` 为权威。奖励展示两秒或威胁成功结算后，先累计完成回合、清理三箱/结果，再进入决策，不自动生箱。决策阶段冻结移动、取消扫描，保留观察；装备组件把键盘 1/2 分别路由到 `ContinueRun()` / `CashOut()`，其他阶段仍执行原装备切换。继续保留 Wallet 金额，恢复移动并生成新三箱；第二次成功收容后原生拒绝继续。

`RunEndReason` 区分 `None/CashedOut/Failed/Error`；T14 构建时使用撤离和技术错误，`Failed` 已在上文 T15 Health 接入。终局快照 `FinalRunValue/CompletedRounds/ThreatsResolved/FinalRunSeconds`，局时钟从首次完整三箱进入可选状态开始。`WBP_RoundDecision : UAnomalyDecisionWidget` 仅显示决策、成功撤离、异常及统计；Coordinator 仍向旧蓝图发 Ended 事件，R 沿用原关卡重载。原“第二次威胁立即 EndRun”“结果后自动下一箱”的叙述仅描述 T14 前版本。构建与待测清单见 `Scripts/RUN_T14.md`。

## T13 三箱回合（2026-10-02 构建，2026-10-04 用户验收）

`AAnomalyRoundCoordinator` 当前轮拥有 `CandidateBoxes`（完整三箱）、`SelectedBox`、`RoundId`；`CurrentBox` 仅保留旧诊断兼容，选箱后指向所选箱。`T13BoxPointLeft/Middle/Right` 是可在 `BP_BoxSpawner` 中调整的固定生成组件，默认相对 Y 为 -220/0/+220 cm。三次独立抽 Safe/Risky/Unknown；全同型时更换一个槽。使用 deferred spawn 在箱子 BeginPlay 前写入公开箱型和轮次 ID；三箱未齐不得交互/扫描，残缺集合销毁并按 1 秒间隔最多重试三次。

`NativeInteract` 先调用 `TryLockSelection(Box)`；只有 Ready、完整候选集合、匹配当前轮次、尚未选箱时成功。成功后所选箱才设置 `bOpened`，其余箱设置 `bSelectionLocked`、关闭 Visibility 射线并显示锁定标记。`CanScan` 走 `IsSelectableBox`，所以 Ready 时可扫描任一候选，锁箱后全部拒绝。`CanResolveBox` 和结果委托只接受本轮 `SelectedBox`；`CleanupCurrentRound` 移除所有候选委托并销毁全部箱子与结果。箱子自身的 `bResolved` 保证重复计时/回调不重复付款。

T13 的源码和 uasset 已构建、独立重载，用户确认测试通过；没有逐项测试记录或独立包报告。旧文中“每轮单箱”“CurrentBox 为唯一箱”的叙述仅描述 T13 前版本。实施与检查入口见 `Scripts/RUN_T13.md`。

## T11E 装备与箱体外观（2026-09-30）

T11 已由用户试玩验收。T11 临时箱型/概率调试标签现已从 C++ 删除；原实现和编译证据保留在 `Saved/T11DebugLabel/`。T11E 的原生装备组件挂于 `BP_FirstPersonCharacter`，开局默认金属探测仪；1 在金属/生物/物质三仪器间循环，2 切枪，从枪按 1 恢复上次仪器。切换时调用 `CancelUse`，手持模型作简短下压切换，枪仅显示“武器功能尚未启用”，没有射击逻辑。Q 扫描与读数仍归 T12。

箱子原生 Actor 根据实例定义概率，用独立随机流分别抽金属加固、警示标记、磨损；视觉附件无碰撞、不改变开箱结果随机流。各类概率遵循 `prototype_v0.2_decisions.md`，包括未知箱三种隐藏配置的统一外观概率。附件挂在现有木箱骨骼网格上，保留原开箱动画。

模型由 `T11EAssets/generate_t11e.py` 可重建，FBX 和 .blend 留在同目录；UE 导入、蓝图引用和独立重载检查入口见 `Scripts/RUN_T11E.md`。2026-10-02 用户反馈 T11E 测试通过；具体测试操作未单独记录。

> 当前迁移说明（2026-09-30）：下文 T00–T11 的 Blueprint 节点、函数图和构建入口是历史设计/实现记录，不能作为当前源码的执行位置。当前运行由 `Source/AnomalyLab` 的 UAnomalyBoxDefinition、UAnomalyWalletComponent、AAnomalyBoxActor、AAnomalyThreatCharacter、AAnomalyRoundCoordinator 实现；同名 BP 保留接口、组件、外观和旧委托适配。实时状态及迁移证据见 `STATE.md`、`CPP_MIGRATION.md`。职责、事件签名、数值和呈现契约继续有效。新功能在 C++ 原生状态/事件接口扩展后，由 Blueprint 负责呈现。

T00–T11E 已验收；T11E 的静态重载证据与用户验收记录见 `Scripts/RUN_T11E.md`。本文描述当前源资产；P0 记录为修改前基线。

## Shared Types

### `EAnomalyOutcome`

- `HighValue`
- `Trash`
- `Threat`

The box owns the random roll. Repeated outcomes are legal. There is no pity or anti-repeat logic.

### `EPrototypeRoundState`

- `Ready`
- `Revealing`
- `OutcomeActive`
- `Ended`

Only `AAnomalyRoundCoordinator` owns and changes the round state. `BP_BoxSpawner.RoundState` is a mirrored legacy enum for player/HUD adapters.

## Interaction Contract

```text
BPI_Interactable.Interact
Input:
    Interactor : Actor Object Reference
```

`BPC_Interaction` must:

- Trace from the First Person Camera through screen center.
- Use the `Visibility` channel and an editable default distance of `300 cm`.
- Track the focused interactable and broadcast focus changes.
- Perform a fresh trace when `E` is pressed.
- Call `BPI_Interactable.Interact` only when implemented by the hit Actor.

It must not Cast to `BP_AnomalyBox`, select outcomes, or let HUD trigger gameplay.

## Box Contract

`BP_AnomalyBox` must:

- Be a project-owned Blueprint Actor implementing `BPI_Interactable`.
- Reference existing wooden-crate art, animation, and sound assets.
- Accept `Interact(Interactor)` and reject duplicate interactions.
- Set `bOpened = true` before broadcasting that opening began.
- Play opening feedback and wait for `RevealDelay`.
- Choose the random outcome and spawn its outcome Actor.
- Request reward payment through the Interactor's `BPC_Wallet`.
- Broadcast the resolved result.

Required dispatchers:

```text
OnBoxOpened(
    Box
)
```

Required timing:

```text
Interact accepted
  ↓
bOpened = true
  ↓
OnBoxOpened(Box)
  ↓
Opening feedback and RevealDelay
```

```text
OnOutcomeResolved(
    Outcome,
    SpawnedActor,
    bSpawnSucceeded
)
```

Required timing:

```text
Outcome selected
  ↓
Outcome Actor spawn attempted
  ↓
Reward payment requested when applicable
  ↓
OnOutcomeResolved(...)
```

The box must not spawn the next box, count Threats, decide Run End, restart the level, or own round state.

## Wallet Contract

```text
AddMoney(Amount)
```

```text
OnMoneyChanged(
    NewMoney,
    Delta
)
```

- Only native `UAnomalyWalletComponent` mutates `Money`. `BPC_Wallet.AddMoney/GetMoney/ResetMoney` delegate to native methods and retain their external Blueprint signatures.
- Default `Money = 0`.
- HighValue requests `AddMoney(HighValueAmount)`, sampled once from the cached definition's inclusive integer ValueMin..ValueMax range (T11; gameplay acceptance pending).
- Trash requests `AddMoney(3)`.
- Threat requests no money.
- HUD displays money but never changes it.
- Restarting `L_Prototype` resets money to zero.

## Loot Contract

- `BP_Loot_HighValue` and `BP_Loot_Trash` are visual result Actors.
- They do not grant money themselves.
- They do not use physics or block the player.
- They remain until the Spawner cleans the current outcome.
- Visual spawn failure does not cancel the selected reward or payment.

## Spider Contract

```text
BP_Spider Parent Class: AnomalyThreatCharacter (inherits Character)
```

Required inherited support:

- CapsuleComponent.
- CharacterMovement.
- AI Controller support.
- `Auto Possess AI = Placed in World or Spawned`.

Visual:

- A selected SciFiWorld Alien Static Mesh attached to the Character.
- The mesh has no skeleton or independent limb/head animation. T10, explicitly requested by the user, adds smooth whole-body yaw toward the player and velocity-driven cosmetic bob/sway/lean. These visual effects must not alter navigation, collision, attack notifications, or threat-resolution timing.

Required API:

```text
ResolveThreat()
```

```text
OnThreatResolved(
    Spider
)
```

Presentation dispatcher:

```text
OnPlayerAttacked(
    Spider
)
```

`BP_Spider` must:

- Acquire the player and chase with `AI Move To`.
- Default to `350 cm/s` and an `80 cm` acceptance radius.
- Overlap, not block, the player.
- Emit attack feedback at most once.
- Resolve at most once.
- Auto-call `ResolveThreat` after three seconds in v0.1.

It must not spawn the next box, count Threats, decide Game Over, modify money, or implement combat.

## Spawner Contract

`BP_BoxSpawner` is the only Round Lifecycle Coordinator.

Owned state:

- `CurrentBox`
- `CurrentOutcomeActor`
- `RoundState`
- `ThreatsResolved`
- Box spawn retry state

It must:

- Spawn the initial box.
- Bind `OnBoxOpened` and `OnOutcomeResolved` on every spawned box.
- Enter `Revealing` when `OnBoxOpened` fires.
- Enter `OutcomeActive` when `OnOutcomeResolved` fires.
- Bind `OnThreatResolved` when a Spider successfully spawns.
- Use a fallback timer when a Threat Actor fails to spawn.
- Clean the current box and outcome Actor.
- Spawn the next box after reward resolution.
- Increment Threat count only after the Threat encounter resolves.
- End the run after the second resolved Threat.
- Retry failed box spawning once per second, at most three times.

```text
Ready
  ↓ OnBoxOpened
Revealing
  ↓ OnOutcomeResolved
OutcomeActive
  ↓ Reward delay or OnThreatResolved
Ready or Ended
```

It must not calculate money, roll outcomes, trace player interaction, or render HUD.

## HUD Contract

`WBP_PrototypeHUD` is presentation only.

Inputs:

- Focus changes from `BPC_Interaction`.
- Money changes from `BPC_Wallet`.
- Outcome messages from the round flow.
- Threat count changes from `BP_BoxSpawner`.
- Run End notification from `BP_BoxSpawner`.

Presentation:

- `Money: $0` in the upper-left.
- `Threats: 0 / 2` below money.
- Small white center crosshair.
- `[E] OPEN` below the crosshair when focus is valid.
- Outcome message at screen center.
- Run Over overlay with final money and restart prompt.

HUD must not calculate money, select outcomes, own round state, spawn gameplay Actors, or use per-frame UMG Property Binding.

## Player Contract

The existing `BP_FirstPersonCharacter` keeps its movement, Mouse Look, Jump, and Camera behavior.

Allowed additions:

- `BPC_Interaction`.
- `BPC_Wallet`.
- Route `IA_Interact` to `BPC_Interaction.TryInteract`.
- Route `IA_Restart` only when the run has ended.
- Create/cache the prototype HUD and connect presentation events.
- Disable movement and interaction on Run End while retaining Mouse Look and `R`.

## Input Contract

- Use a separate `IMC_Prototype`.
- Do not modify template movement mappings without a proven need.
- `IA_Interact` maps to `E` with a `Started` trigger.
- `IA_Restart` maps to `R` with a `Started` trigger.
- Restart is ignored unless the round is `Ended`.

## Level Contract

- Gameplay map: `/Game/Prototype/Maps/L_Prototype`.
- Reuse existing `BP_FirstPersonGameMode`.
- Level Blueprint contains no round gameplay logic.
- `BP_BoxSpawner` is placed at the central pedestal.
- Industrial door remains closed and non-interactive.
- NavMesh covers the playable laboratory floor.

## Future Combat Contract

Combat is not implemented in v0.1. Future combat must:

1. Configure `AAnomalyThreatCharacter`'s auto-resolution for the new rule; preserve a callable `ResolveThreat()` for confirmed monster death.
2. Block the next box while a Threat remains unresolved.
3. Call `ResolveThreat()` from confirmed monster death.
4. Increment Threat count only after that call.
5. Continue after the first defeated Threat.
6. End the run after the second defeated Threat.
7. Preserve Interaction, Wallet, Box random selection, HUD ownership, and Spawner ownership.

## Contract Violation Rule

If implementation appears to require violating this file, stop and report the exact contract, technical reason, and smallest proposed change. Do not silently redesign the architecture.

## 当前蓝图实现索引


`BPC_Interaction.TryInteract` → `BPI_Interactable.Interact(Interactor)`。不 Cast 到具体箱子。
箱子验证 Interactor 和 bOpened，置 bOpened 后广播 `OnBoxOpened(Box)`；播放反馈，延迟约一秒；按 bResolved 防重复后确定 Outcome，生成结果、请求 `BPC_Wallet.AddMoney(Amount)`，最后广播 `OnOutcomeResolved(Outcome, SpawnedActor, bSpawnSucceeded)`。
Wallet 通过 `OnMoneyChanged(NewMoney, Delta)` 更新显示。HUD 只负责展示，使用事件更新。

Spawner 的 `HandleBoxInteractionStarted`、`HandleOutcomeResolved`、`HandleThreatResolved` 驱动状态：Ready → Revealing → OutcomeActive → Ready 或 Ended。
奖励等待 `RewardElapsed`；蜘蛛通过 `ResolveThreat()` 广播 `OnThreatResolved(Spider)`；生成蜘蛛失败用 `ThreatFallbackElapsed`。`CompleteCurrentOutcome` 统一处理计数，`CleanupCurrentRound` 清理计时器、委托与 Actor。`SpawnNextBox`/`RetryBoxSpawn` 负责下一盒及有限重试，`EndRun` 负责结束。
Spider 通过 `OnPlayerAttacked(Spider)` 通知一次接触攻击。三个 Actor 委托参数已在 T06 修复为显式 Self 连接。

Spawner 向界面发送 `OnOutcomeMessage`、`OnThreatCountChanged(Count, Maximum)`、`OnAttackMessage`、`OnRunEnded(bError)`。角色 `T06RunEnded` 锁定移动和交互并保留观察，`T06Restart` 仅在 Ended 重载 L_Prototype。


### Spawner → Character / HUD 的委托签名

```text
OnOutcomeMessage(Outcome : EAnomalyOutcome, SpawnedActor : Actor, bSpawnSucceeded : bool)
OnThreatCountChanged(Count : int, Maximum : int)
OnAttackMessage()
OnRunEnded(bError : bool)
```

Character 缓存 T06Spawner/HUD；由事件更新 UI，不用每帧 UMG Property Binding。
T06RunEnded 必须先执行 Wallet.GetMoney，再展示最终金额与锁定移动。T06Restart
仅在 Ended 生效。回调中的 Actor 参数使用实际对象/Self 连线，不能用字符串默认值代替。

### 当前关键默认值

以下来自 STATE、契约及已验收构建记录；P0 已在 UE 内重新读取核心蓝图类默认值并记录于 Saved/P0 的 unreal_inspection.json。地图导航覆盖、动作外观和实际输入不属于该只读检查的证明范围。

| 系统 | 默认值 / 行为 |
|---|---|
| Interaction | 300 cm；焦点更新间隔 0.05 s；E 时重新射线 |
| Box | bOpened=false、bResolved=false；RevealDelay=1.0 s；正常游玩 bForceOutcome=false；bDebugLogging=true |
| Outcome | T11 按实例权重选择；HighValue 按配置金额区间抽整数、Trash +3、Threat 不加钱 |
| Wallet | Money=0 |
| Spider | MoveSpeed=350；AcceptanceRadius=80；攻击重叠半径 80 cm；视觉高度 90 cm |
| Spider 结算 | bAutoResolveThreat=true；AutoResolveDelay=3.0；bResolved=false、bAttackTriggered=false |
| Spider 寻路 | 首次失败后 0.5 s 重试一次；自动结算独立调度 |
| Spawner | Ready；ThreatsResolved=0；MaxThreats=2；NextRoundDelay=3.0 |
| Spawner 重试 | SpawnRetryDelay=1.0；MaxSpawnRetries=3；CurrentSpawnRetryCount=0 |
| Spawner 引用 | CurrentBox、CurrentOutcomeActor、CurrentSpider 初始为空；BoxClass=BP_AnomalyBox |
| 布局 | Spawner/箱子 Z=50；CreatureSpawnPoint 相对 (250,-300,-3) |


### 蜥蜴轻量动作实现（T10，用户已验收）


- Tick 在未结算时调用 `T10FacePlayer` 和 `T10AnimateBody`。
- 前者验证玩家有效，水平距离小于 1 cm 时保留朝向；使用 RInterpTo 平滑朝向玩家，
  目标俯仰/侧倾均为零。关闭运动组件/控制器的竞争转向。
- 后者根据实际水平速度驱动。5 cm/s 以下目标幅度为零，350 cm/s 时为全幅，
  FInterpTo 平滑过渡。相位按行进距离推进，约每 115 cm 一个周期。
- 仅对 AlienVisual 改相对位置和旋转：正向轻微起伏、交替侧摆、少量前倾和点头。
  相对位置始终基于保存的中性位置重新计算，不累加位移。
- AI MoveTo、导航、角色移速、碰撞/攻击范围、3 秒自动结算及两次 Threat 结束保持原样。

#### T10 动作参数

| 变量 | 默认 | 意义 |
|---|---:|---|
| T10TurnSpeed | 8 | 朝向插值速度 |
| T10StrideLength | 115 cm | 一个动作周期的行进距离 |
| T10BobHeight | 2 cm | 上下起伏幅度 |
| T10SwayDegrees | 2° | 左右侧摆 |
| T10LeanDegrees | 2.5° | 移动时前倾 |
| T10PitchDegrees | 1° | 点头幅度 |
| T10BlendSpeed | 8 | 移动/停止时幅度过渡速度 |
| T10MotionScale | 1 | 0 可关闭身体动作，保留朝向；限制到 0..1 |


`T10FacePlayer(DeltaSeconds)` 与 `T10AnimateBody(DeltaSeconds)` 均是 BP_Spider 内部函数。
T10Phase/T10MoveBlend 初始为 0；T10BaseLocation 保存原 AlienVisual 中性相对位置。
T10MotionScale 限制到 0..1；步幅计算至少使用 10 cm，避免零除。
Actor 只做水平转向，AlienVisual 独立做相对变换；原 AI MoveTo、碰撞和结算链保留。
模型正前方为 +X；头颈及四肢不单独运动，绕障碍时可能出现侧向滑行。

构建入口：`Scripts/build_t10.py` / `Scripts/RUN_T10.ps1 -Mode build`；独立重载检查：
`Scripts/RUN_T10.ps1 -Mode validate`。运行前关闭其他 UE 编辑器，允许标准缓存写入。
启动器使用隐藏 NullRHI 后台进程，进程级禁用 MCP 插件，不修改 uproject 插件配置，
不运行 PIE。构建先备份并分阶段保存/重载；已完成标记会使重跑保留现有实现。
备份位置由 `Saved/T10/baseline.json` 指定。不要将旧构建脚本当作无条件覆盖工具。

### 后续修改的最小回归要点

验证 HighValue 金额在当前实例区间内、Trash +3 及同局累计；快速重复 E 不重复开箱/付款；
两次 Threat 分别结算到 1/2 与 2/2，结束后不再生箱；R 重开重置状态；
蜥蜴移动时朝向和身体动作正常，停止时收敛，不影响接触通知和三秒结算。
涉及失败路径时检查有限生成重试、Threat fallback、奖励外观失败仍付款和旧回调保护。
测试强制结果只改临时实例，结束后保持 bForceOutcome=false，不保存故障注入。
日志按 [Interaction]/[Box]/[Wallet]/[Threat]/[Round]/[HUD] 与测试时间过滤。
实体输入、视觉和独立打包运行须实际验证；结构检查不能代替它们。

### T11 箱子数据（2026-09-27 构建，2026-09-30 用户验收）

采用 `BP_AnomalyBoxDefinition : PrimaryDataAsset` 加六个定义实例；精确路径见 ASSET_MAP。
这是原总体计划允许的数据资产方案，替代因本机公开 Python 缺少 Struct 字段编辑 API 而不可直接构建的 Struct/DataTable 默认方案。

| 定义 ID | HighValue / Trash / Threat | 高价值金额 |
|---|---|---|
| Safe | 0.30 / 0.60 / 0.10 | 500–1500 |
| Risky | 0.55 / 0.10 / 0.35 | 3000–6000 |
| Unknown（基础参考，初始化后替换为隐藏配置） | 0.40 / 0.35 / 0.25 | 500–7000 |
| UnknownSafe | 0.35 / 0.55 / 0.10 | 500–2000 |
| UnknownMedium | 0.40 / 0.35 / 0.25 | 1500–4500 |
| UnknownRisky | 0.45 / 0.15 / 0.40 | 3000–7000 |

15 个定义字段：BoxID、DisplayName、ValueMin/Max、三项 Chance、ValueLowerScale/UpperScale、ScanProbabilityError、RandomHiddenProfile、HiddenProfile、MetalChance、WarningChance、WearChance。
上述是 T11 的数据契约；外观字段已由 T11E 使用，扫描字段已由 T12 使用（2026-10-02 用户验收通过）。

- `DefinitionID=None`：等权抽 Safe/Risky/Unknown；显式 ID 可供后续 Spawner 或调试指定。Unknown 生成时等权抽三套隐藏配置；三个隐藏资产 DisplayName 均为“未知箱”。内部 ID 和精确概率未接入 HUD。
- `T11InitializeDefinition()` 在 BeginPlay 调用；Interact 在置 bOpened 前还会调用一次作为保护。bDefinitionInitialized 防重复，不重抽配置。
- `T11LoadDefinition()` 检查 ID 和资产引用，复制 15 个字段到箱子 `Data*` 变量；不修改共享定义资产。ResolvedDefinitionID 记录实际配置，DefinitionAsset 保留来源引用。
- `T11ValidateDefinition()` 验证概率各在 0..1、总和与 1 差值不超过 1e-6、0 <= ValueMin <= ValueMax <= 2147483646，以及扫描和外观参数范围。失败时 bDefinitionValid=false，拒绝开箱并记录错误；此阶段不新增 Error 终局。
- ConfigurationStream 只用于类型/隐藏配置抽取，OutcomeStream 用于结果/金额。初始化时分别创建种子；bUseFixedSeeds=false 为生产默认值，开启后使用 ConfigurationSeed=11001、OutcomeSeed=11002 供后续测试。
- `T11RollOutcome()` 缓存一次 [0,1) 抽样，按累计概率写入旧 OutcomeRoll=0/1/2，再进入原结果分支。
- `T11RollReward()` 在随机和强制 HighValue 两个分支的展示 Actor 生成前各接入一次，缓存整数金额供原 Wallet 调用读取。垃圾 3、威胁无付款、奖励外观失败仍付款的旧链路保留。
- bForceOutcome/ForcedOutcome 原路径保留且默认关闭；初始 HighValueAmount=0，实际高价值金额只在揭晓时生成。原有 bOpened/bResolved、委托和一秒反馈顺序保留。

构建入口 `Scripts/RUN_T11.ps1`；`Saved/T11/build.json` 与 `reload.json` 记录构建/重载，备份由 baseline.json 定位。
PIE、概率抽样、实体输入、视觉、失败注入与重开均未在本轮执行；待测清单见 Scripts/RUN_T11.md。

### T12 扫描契约（2026-10-02 构建及用户验收通过）

- `UAnomalyScannerComponent` 独立于 BPC_Interaction；使用相机中心 300 cm Visibility 射线，通过 `IAnomalyScanTarget` 访问目标，不修改现有 E 交互图。以 PostUpdateWork Tick 采样玩家 Q/E 输入，在移动/交互之后复核目标再完成扫描。
- `IAnomalyScanTarget.CanScan/GetCachedReading/CompleteScan` 由原生 Box 实现。CanScan 要求定义有效、未开/未结算、Coordinator Ready，且箱子属于本轮完整候选集合、未被锁定；T13 后由 `IsSelectableBox` 校验。
- 按住 Q 一秒才完成未扫描的仪器；松开、切目标/装备、遮挡、距离超限、非可用阶段或 E 取消并清零，需要释放再按 Q。装备 `CancelUse` 与 Box `NativeInteract` 同步调用 `CancelScan`，防止同帧开箱/切装备完成旧扫描。
- Box 的瞬态 ScanCache 按仪器保存 `FAnomalyScanReading`，读取实例 DefinitionAsset 副本，不初始化/重抽配置，不访问 ConfigurationStream/OutcomeStream/VisualStream，不付款。缓存随箱子销毁，重新对准只恢复该箱的已扫描项目。
- 金额下/上限按 ValueLowerScale/ValueUpperScale 扩展并向外取整至百元（int64），浮点整百误差作稳定化处理。概率按 ScanProbabilityError 扩展后裁剪 0..1；威胁等级阈值 .15/.30，高价值等级阈值 .35/.50，边界归较高等级。高/低可靠性由当前定义干扰配置判断。
- HUD 数据仅含 bScanned、ValueMin/Max、Level、Reliability，不含精确概率、隐藏配置名或最终 Outcome。未扫描项显示“未扫描”；金额标注仅指高价值结果，等级不保证本次结果。
- `WBP_ScanPanel : UAnomalyScanWidget` 为现有 HUD 的独立展示扩展，由 Scanner 创建/清理，只接收展示数据；不控制游戏、不监听按键、不写钱包。内容变化时更新控件，没有 UMG 每帧属性绑定。Ended 隐藏扫描层，R 重载创建全新组件/界面。
- 2026-10-02 用户确认 T12 测试完成且无问题，人工验收通过；未提供逐项记录，不据此声称数学边界/同种子结果流自动回归或独立包验收通过。入口 `Scripts/RUN_T12.md`，记录 `Saved/T12/acceptance_log.md`。


## v0.3 探索模式权威接口（2026-10-11）

- `AAnomalyRoundCoordinator.PlayMode` 默认 LegacyPrototype；仅 L_Prototype 地图实例为 Exploration。
- `SpawnLoot` 仅接受当前选定回合与合法开奖阶段，每回合最多生成一次。`UAnomalyItemDefinition` 是固定展示数据；`FAnomalyItemInstance` 包含唯一 Guid、ItemId、名称、确定价值和来源 RoundId。TrashValue 固定 3；拾取不抽随机数。
- `UAnomalyInventoryComponent` 运行时作为玩家实例组件创建，四格、不堆叠、不存档。私有 `TryStore` 在游戏线程先写所有权与清单，再隐藏销毁代理；Widget 只读 `Describe` 快照。满格不改变世界 Actor。
- `TryPickup` 复核玩家身份、世界清单、生命/终局、相机 Visibility 射线和 300 cm。E 优先拾取；同帧成功/拒绝满格后禁止对后方箱子双触发。箱子仍复用旧 Blueprint E 适配，但 C++ 复核相机目标与阶段。
- `CashOut` 在探索模式只进入 ReturningToExtraction；二次收容自动进入该阶段，ContinueRun 拒绝。`ConfirmExtraction` 要求入口 XY 325 cm / 高差 180 cm / 无遮挡、合法阶段、玩家存活。付款下一帧复核；死亡事件优先。
- `EndRun` 在任何 Wallet 展示回调前封闭全部玩法入口。成功仅能由物理入口授权，结算一次；死亡记录 CarryValue 损失、收入 0，Error 不伪装成撤离。终局清空背包/世界物品/箱子/威胁/计时器，R 重载当前地图重置。
- `FeedbackSounds` 为探索地图持有的本地 SoundWave 引用，`EmitFeedback` 仅由事件触发；扫描开始音在取消时停止。应急光常亮，方向/距离、扫描进度、拾取/满格、伤害文本在静音时仍有效。音效计数用于自动诊断，不维护玩法权威。
- `-AnomalyV03Smoke` 仅供 Development 自动化；强制结果/故障均为临时实例。`-V03Strategy=` 走实际导航并采用非强制开奖。它们与正常启动分离，无参数时不产生测试 Actor。

## v0.4 T30 Observer（2026-10-12）
- 探索区域池支持 Chaser/Observer；混合池观察者35%，类型独立随机流。Legacy 仍仅原追逐者。
- 眼部20m内、相机点积进入0.8/退出0.72、Visibility无遮挡才有效；获取0.08s、失视0.18s、最短驻留0.2s。正视停步，背向/遮挡接近。
- 累计注视4s触发明示红眼1.25s；不受诱饵影响。伤害前0.35s容错，其余速度/伤害/冷却/20s收容/终局死亡优先契约保持。
- 仅 Development 显式 -AnomalyObserverSmoke 安装观察者验证驱动，正常启动不运行；测试槽强制 Automation_ 前缀。
