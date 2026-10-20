# Anomaly Lab Prototype v0.1 项目总结

> 2026-09-30 当前源码已完成核心 C++/Blueprint 混合迁移；本文件其余内容是已验收 v0.1/T10 的历史总结，固定奖励与纯蓝图执行位置不代表当前实现。当前事实见 `Docs/STATE.md` 和 `Docs/CPP_MIGRATION.md`。

> 当前源码补充（2026-09-27）：T11 箱子数据资产已通过 Python 构建、编译和重载，尚未进行玩法测试。高价值金额和结果概率现由定义资产驱动，详见 Docs/STATE.md 与 Docs/01_CONTRACTS.md。下文保留 v0.1+T10 已验收基线总结；其中固定 +5000、等概率等规则不再代表 T11 源码。旧 T09 打包版本未变。

更新日期：2026-09-24  
结论：原计划 T00–T09 与后续 T10 轻量蜥蜴视觉扩展全部完成，用户已于 2026-09-24 确认 T09、T10 测试完成。当前源码含 T10；现有 Windows Development 包为 T09 版本，尚不包含 T10。

## 1. 原型完成了什么

项目使用 Unreal Engine 5.8，以 Blueprint 实现单机第一人称异常开箱循环。玩家在封闭实验室中接近中央木箱，通过准星和 E 交互，观察开箱反馈，获得随机奖励或遭遇追逐怪物。系统清理本轮结果后生成下一只箱子；累计完成两次威胁遭遇后结束本局，显示最终金额，并允许按 R 从头开始。

这次原型验证了交互、随机结果、金额、威胁与轮次生命周期能够连接成完整可重复体验，并完成了从编辑器 PIE 到 Windows Development 打包交付的流程。

## 2. 玩家体验与规则

```text
进入实验室：Money $0，Threats 0/2，一个未开启的箱子
  → 300 cm 内瞄准，显示 [E] OPEN
  → 按 E，箱子只开启一次，播放动画与声音
  → 约 1 秒后随机选择 HighValue / Trash / Threat
      HighValue：生成金条外观，金额 +5000
      Trash：生成椅子外观，金额 +3
      Threat：生成蜥蜴外观的 BP_Spider，追逐玩家，不加钱
  → 奖励约 3 秒后清理；威胁约 3 秒后结算并清理
  → 未达两次已结算 Threat：生成下一只箱子
  → 第二次 Threat 结算：Run Over，显示最终金额
  → 按 R 重载关卡，金额、威胁数、界面和对象引用重置
```

- 随机整数范围为 0..2，对应三种结果；允许连续重复，没有权重或保底。
- WASD 移动、鼠标观察和跳跃沿用 First Person Template；角色行走速度按用户要求设为 350。
- Run Over 后禁用移动和开箱，保留观察和 R；运行中 R 不重开。
- “攻击”只是一条接触通知和界面提示，没有伤害、生命值或死亡。
- 威胁次数在遭遇结算时增加，不在怪物刚生成时增加。

## 3. 实现结构与职责

下表资产路径均以 `/Game/` 开头；完整路径见 `Docs/ASSET_MAP.md`。

| 资产或系统 | 负责内容 |
|---|---|
| `Prototype/Maps/L_Prototype` | 实验室地图、底座、出生点、导航和单个 BoxSpawner；默认启动地图 |
| `Prototype/Environment/LowPolyLab` | 实验室静态网格与基础材质 |
| `Interaction/BPI_Interactable` | 定义 Interact(Interactor) 接口 |
| `Core/Components/BPC_Interaction` | 相机中心 Visibility 射线、焦点提示、E 时重新检测并调用接口 |
| `Anomalies/Containers/BP_AnomalyBox` | 防重复开箱、动画声音、随机结果、生成结果 Actor、请求发钱和通知结果 |
| `Core/Components/BPC_Wallet` | 唯一金额修改者，通过 OnMoneyChanged 通知界面 |
| `Anomalies/Loot/BP_Loot_HighValue`、`BP_Loot_Trash` | 金条和椅子展示，不独立发钱，不阻挡玩家 |
| `Anomalies/Creatures/BP_Spider` | AI 追逐、一次攻击通知、一次威胁结算；视觉为 Alien06 静态蜥蜴 |
| `Anomalies/Containers/BP_BoxSpawner` | 唯一轮次协调者，管理生成、回调、清理、威胁数、重试和结束 |
| `UI/WBP_PrototypeHUD` | 金额、Threats、准星、交互提示、结果/攻击消息和结束界面 |
| `FirstPerson/Blueprints/BP_FirstPersonCharacter` | 输入路由、创建/缓存 HUD、连接事件、结束控制和 R 重载 |
| `Core/Input/IA_Interact`、`IA_Restart`、`IMC_Prototype` | 独立的 E/R 输入配置，保留模板移动绑定 |
| `Core/Types/EAnomalyOutcome`、`EPrototypeRoundState` | 结果和轮次枚举 |
| `Core/Debug/BFL_PrototypeLog` | Info / Warning / Error 日志辅助 |

箱子决定随机结果，Wallet 决定金额，Spawner 决定轮次，HUD 只展示。交互组件不 Cast 到具体箱子，Level Blueprint 不承担轮次逻辑。稳定接口定义在 `Docs/01_CONTRACTS.md`。

## 4. 关键参数与保护（玩法基线；T10 动作参数见接口文档）

| 项目 | 已验收基线 |
|---|---|
| 交互距离 / 焦点检测间隔 | 300 cm / 0.05 s |
| 开箱揭示延迟 | 1.0 s |
| 奖励 | HighValue +5000；Trash +3；Threat +0 |
| 蜥蜴移速 / AI 到达半径 | 350 cm/s / 80 cm |
| 蜥蜴视觉 | SM_CreatureAlien06-Pose2，约 90 cm 高，无骨骼动画 |
| 威胁自动结算 | 3.0 s |
| 结束条件 | 两次已结算 Threat |
| 奖励清理与下一轮等待 | 3.0 s |
| 箱子生成失败 | 初次失败后最多重试 3 次，间隔 1.0 s，耗尽后 Prototype Error |
| 箱子位置 | 中央底座 Z=50 cm |
| 怪物生成偏移 | 相对箱子 (250, -300, -3)，避开底座与立即接触 |

对象使用前验证有效性；开箱、结果、攻击和威胁结算设置一次性保护。过期或重复回调不应重复付款、计数或生成。奖励外观生成失败仍请求付款；怪物生成失败由 Spawner 的 fallback 计时器完成结算。AI 首次寻路失败等待 0.5 s 重试一次；独立自动结算不因寻路失败而卡住。

## 5. 实施里程碑与验收依据

| Ticket | 完成内容 | 完成日期 / 依据 |
|---|---|---|
| T00 | 项目预检、实验室与基础类型 | 2026-09-08，记录 PASS |
| T01 | 交互接口、射线、焦点与 E 输入 | 2026-09-12，结构和 PIE 记录 |
| T02 | 一次性开箱与反馈 | 2026-09-12，结构检查及用户 PIE 验收 |
| T03 | 三类随机结果与调试强制模式 | 2026-09-13，强制结果及 18 次随机样本 |
| T04 | Wallet、奖励外观与 HUD | 2026-09-17，用户人工确认 |
| T05 | 怪物追逐、攻击通知与结算 | 2026-09-20，构建/结构/PIE 证据及用户确认 |
| T06 | 重复循环、两次威胁结束、重开 | 2026-09-22，构建和部分自动证据及用户确认 |
| T07 | 综合验收与实现文档 | 2026-09-23，部分自动检查及用户总体确认 |
| T08 | 用户最终 PIE 验收 | 2026-09-23，用户确认，接受静态蜥蜴外观限制 |
| T09 | Windows Development 打包与冒烟验收 | 2026-09-23 打包成功；2026-09-24 用户确认完成 |
| T10 | 整体面向玩家及轻量身体动作 | 2026-09-23 编译保存；2026-09-24 用户确认测试完成 |

自动证据与人工验收分开记录。T03 的历史随机样本为 HighValue 6、Trash 8、Threat 4，不冒充 T07 或 T09 的新样本。T07 修复过最终金额读取执行连接；T06 修复过枚举与 Actor 委托 Self 参数。原始日志和 JSON 保留了构建/测试证据；阶段 Markdown 已合并清理。

T09 自动构建返回 ExitCode=0，含 BUILD SUCCESSFUL，Cook 汇总 0 errors / 0 warnings，打包清单包含 L_Prototype；构建当时 19 个核心源包哈希一致。用户本次确认 T09 已完成，但未额外提交逐项结果或新的运行日志；本总结不据此编造新的自动测试结果。

## 6. 交付物与复现入口

| 项目 | 位置 |
|---|---|
| 源工程 | `F:/AnomalyLab/我的项目3/我的项目3.uproject` |
| 已验收包目录 | `F:/AnomalyLab/我的项目3/Builds/T09/20260923T090604Z/Windows/` |
| 包启动入口 | 上述目录内 `AnomalyLabT09.exe`；保留整个 Windows 目录 |
| 打包脚本 / 说明 | `Scripts/build_t09.py` / `Scripts/RUN_T09.md` |
| 精确构建命令及源包哈希 | `Saved/T09/20260923T090604Z/build.json` |
| 自动打包日志 | `Saved/T09/20260923T090604Z/packaging.log` |
| 当前事实 / 接口 / 路径 | `Docs/STATE.md` / `01_CONTRACTS.md` / `ASSET_MAP.md` |
| 蓝图函数、委托签名、调用顺序和 T10 参数 | `Docs/01_CONTRACTS.md` |
| 后续维护规则 | `Docs/00_RULES.md` |

打包使用 Win64 / Development、Pak + IoStore，显式包含 L_Prototype。为绕过本机 MSVC 中文路径问题，脚本复制工程到英文路径 `F:/AnomalyLab/T09BuildWork/<时间>/AnomalyLabT09.uproject` 构建；补充 GameFeatureData 扫描配置解决 Cook 阻塞，没有增加玩法 C++ 或修改资源包原件。

**重新运行打包脚本会使用当前源工程，不能假定它与已验收包完全一致。** 当前源工程已有 T10 改动，而上述交付包仍是 T09 基线。

## 7. 当前限制与后续扩展

当前源码中怪物为静态蜥蜴模型，已加入整体面向玩家、随移动起伏/侧摆/前倾；没有真正迈步、独立头颈转动或战斗动画。旧 T09 包仍为此前静态滑行表现。只有一个固定箱点，未加入存档、主菜单、设置、联网、背包、商店、检测设备、生命值、伤害或死亡系统。没有 Shipping 包或安装器。美术音效仍属原型，攻击提示保留冗余调试 PrintString。

T10 已由用户确认测试完成。BP_Spider 内 `T10FacePlayer(DeltaSeconds)` 和 `T10AnimateBody(DeltaSeconds)` 分别处理整体水平朝向与速度驱动身体动作，保留现有追逐、碰撞和三秒结算；详细参数与连线职责见 `Docs/01_CONTRACTS.md`。本次用户确认属于人工验收，没有补造完整自动验证 PASS：旧验证脚本曾在节点名称断言处停止，修正后未完成自动重跑。这不影响记录用户已完成的测试确认。

当前无待完成的已授权开发任务。后续如需把 T10 交付为独立程序，需要从当前源码重新打包并测试；旧 `build_t09.py` 的阶段预检仍限定 T09/T08 状态，使用前须调整预检，不能回退 STATE 以迎合旧脚本。本次仅清理文档，未改脚本或重新打包。

未来若另行批准战斗系统，可关闭 `bAutoResolveThreat`，在确认死亡时调用 `ResolveThreat()`；Spawner 继续通过 OnThreatResolved 计数和推进，保留当前职责边界。该入口已预留，但战斗本身未实现。

## 8. 后续接手的阅读入口

保留 8 份 Markdown：本总结；Docs 下 STATE、01_CONTRACTS、ASSET_MAP、00_RULES；
Scripts/RUN_T09.md；两个源模型目录的 README_GENERATION.md。
先看 STATE 确认版本，再看接口文档了解函数和事件链，最后按 ASSET_MAP 定位蓝图。
已完成任务说明、阶段验收和中间测试 Markdown 已删除；脚本、原始日志/JSON、备份和资产原样保留。
