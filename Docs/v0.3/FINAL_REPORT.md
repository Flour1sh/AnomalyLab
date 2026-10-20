# AnomalyLab v0.3 发布候选报告

> 此报告冻结记录基础 RC_20261011T220432；后续场景升级、新包与当前验证见 `Docs/v0.3/SCENE_POLISH.md`。

> 后续用户确认（2026-10-11）：已完成人工测试并认可，授权继续优化场景。下文 PENDING_MANUAL 为交付当时记录；不补造逐项测试结果。确认与新美术范围见 `Saved/ScenePolish/acceptance_log.md`。

更新：2026-10-11。C++ 与 Python 资产构建、最终包自动验证全部完成（DONE）；人工实体输入、听感与试玩验收为 `PENDING_MANUAL`。用户授权完成全部 v0.3 并自行自动化测试，人工测试随后进行。本轮未调用 UE MCP、未接管屏幕、未修改项目的扩展配置。

## 交付入口

- UE 5.8 / Win64 Development：`Builds/v0.3/AnomalyLab_RC_20261011T220432/Windows/AnomalyLab.exe`。正常双击，无需测试参数；保留整个 Windows 文件夹。较早的 RC/T19 包是历史产物。
- 原工程：`我的项目3.uproject`，Editor 模块已部署；默认 `L_MainMenu`，开始游戏进入 `L_Prototype`（Level01）。
- 运行与人工清单：`Scripts/RUN_V03.md`。最终包与构建日志索引：`Saved/V03/package_report.json`；源码/资产清单：`Saved/V03/package_source_20261011T220432.json`。

## 已实现

| 阶段 | 交付 |
|---|---|
| T19 | 独立菜单、开始/设置/指南/退出确认、正确切图与恢复玩法输入；指南更新为实体拾取和返回兑现规则 |
| T20 | 入口、走廊与 A/B/C 三房；三个分离候选箱、绿色返回路线、导航与碰撞；Legacy 地图保留 |
| T21 | 实验芯片、异常核心、密封样本、废旧电池四类实体；发光外观；金额开奖时确定一次；垃圾固定 $3 |
| T22 | 玩家权威四格背包；300 cm 相机射线 E 拾取、满格保留物品、同帧优先级与重复领取保护；跨轮携带 |
| T23 | 开箱/拾取不入 Wallet；2 只确认返程意图，入口 E 下一帧复核后一次性兑现；死亡丢失携带、收入 0；独立 Error；二次收容强制实际返程；R 全部重置 |
| T24 | 扫描进度/可靠性/取消反馈、既有开箱机械动画与声音、实体发光与拾取音、预警/常亮红光/方向距离、追逐音源、受伤遮罩/音效、撤离反馈；新增 9 种本地生成音效 |
| T25 | 原生真实地图自动化、三策略导航机器人样本、两档实际渲染、Legacy 回归、Win64 独立包与人工试玩清单 |

箱型/结果随机流、选一锁二、Q 一秒扫描与缓存语义继续复用。探索箱新增动态导航阻挡，防止机器人寻路穿过箱体；近战增加遮挡检查。Legacy 保留直接奖励与旧终局规则。

## 验证结果与边界

| 项目 | 自动断言 | 实际渲染/截图 | 人工真实操作 |
|---|---|---|---|
| 独立资产重载 | 36/36 PASS；6 个 Blueprint 编译、4 个定义、9 个 SoundWave、生产默认值与地图引用 | 材质 D3D12 预热 12 项 PASS | 不适用 |
| Editor 完整连续流程 | 146/146 PASS，默认菜单到玩法与重开 | 此次为 NullRHI；另有早期 720p 渲染记录 | PENDING_MANUAL |
| 最终包 1280×720 | 151/151 PASS，菜单启动另 3/3 | 18 张 D3D12 实景；已核对扫描/满格/威胁/终局 | PENDING_MANUAL |
| 最终包 1920×1080 静音 | 151/151 PASS，菜单启动另 3/3 | 18 张 D3D12 实景；中文/扫描/终局已核对，禁用音频 | PENDING_MANUAL |
| 最终包独立菜单两档 | 各 21/21 PASS | 各 6 张实景；默认启动、设置、指南、退出确认、加载、Level01 | PENDING_MANUAL |
| Legacy Editor | stats 52/52、decision 47/47、flow 66/66 PASS | NullRHI 逻辑回归 | 历史验收不扩写 |
| Legacy 最终包 | stats 52/52、decision 47/47、flow 66/66 PASS | NullRHI 逻辑回归 | PENDING_MANUAL |
| 交付一致性审计 | 267/267 PASS | 86 份源文件/资产与 ASCII 副本、最终二进制、48 张截图尺寸一致 | 不适用 |

数字是执行的断言检查点，包含不同回合重复验证同一规则，不代表同等数量的独立测试用例。自动驱动合成 PlayerController 按键及 UMG 按钮事件；边界分支使用临时强制结果、传送和故障注入，生产默认强制结果与固定种子均关闭。渲染路线实际步行前往首房和入口；威胁保持默认 20 秒，未用免伤或提前解决伪造存活。

连续主路线在同一局中从默认菜单开始，完成扫描、四件 Loot 携带、满格拒绝、继续、一次真实威胁存活、选择撤离、物理返程、结算和 R 重开。其余场景另覆盖两次收容、死亡损失、空包撤离、确认同帧死亡优先、迟到回调、错误定义和未授权直接终局。

截图为后台实际渲染保存的证据；本轮没有人工实时录屏，也没有实体键鼠或音效听感验收。静音渲染证明视觉信息存在，不能代替人类可读性/操作感判断。

## 三策略样本

| 策略 | 游戏用时 | 带出 | 丢失 | 死亡 | 扫描 | 回合 |
|---|---:|---:|---:|---|---:|---:|
| 保守 | 32.732 秒 | $636 | $0 | 否 | 2 | 2 |
| 贪婪 | 76.413 秒 | $18384 | $0 | 否 | 5 | 5 |
| 随机 | 39.499 秒 | $3977 | $0 | 否 | 3 | 3 |

每种策略仅 1 次机器人真实导航/实际扫描/非强制开奖样本，使用公开箱型选择，不是三种人类试玩样本。单次均存活不能推断总体死亡率；这些快速机器人样本不证明达到 3–5 分钟的人类体验目标。汇总 `Saved/V03/strategy_samples.json`；各次原始报告由 `latest_{策略}_logic_1280x720.json` 定位。

## 文件与证据

- 新原生类：`Source/AnomalyLab/Public/AnomalyItemDefinition.h`、`AnomalyWorldPickup.h`、`AnomalyInventoryComponent.h`、`AnomalyV03Smoke.h` 及对应 Private 实现；主要扩展 Coordinator、Box、Scanner、Threat、ExplorationWidget、DecisionWidget、MenuSmoke。
- 新资产：`Content/Prototype/Data/Items/`、`Content/Prototype/Audio/`；修改 `Content/UI/WBP_ExplorationPrompt.uasset`、`Content/UI/Menu/WBP_MainMenu.uasset`、探索地图的实例引用。精确接口/路径见 `Docs/01_CONTRACTS.md`、`Docs/ASSET_MAP.md`。
- 资产构建：`Scripts/build_v03_loot.py`、`build_v03_ui.py`、`build_v03_feedback.py`、`polish_v03_ui.py`；预热/重载：`warm_v03.py`、`verify_v03_assets.py`。
- 自动化/交付：`Scripts/run_v03.py`、`run_t19_menu.py`、`run_t18.py`、`package_v03.py`、`audit_v03_delivery.py`。完整命令见运行指南。
- Editor 连续逻辑：`Saved/V03/Runs/20261011T220419438091_logic_1280x720/`。
- 最终包 720p：`Saved/V03/Runs/20261011T220823609934_render_1280x720/`。
- 最终包 1080p：`Saved/V03/Runs/20261011T221131782761_render_1920x1080/`。
- 最终菜单两档：`Saved/T19Menu/RenderRuns/20261011T221458_1280x720/`、`20261011T221521_1920x1080/`。
- 最终审计：`Saved/V03/delivery_audit.json`，确认当前源码/资产、编译副本、Editor DLL 与最终游戏二进制一致，106 个既有保护资产及 Legacy 地图哈希保持一致，项目插件配置未改。
- Legacy 最终包日志：`Saved/T18/packaged_stats_20261011T220835.log`、`packaged_decision_20261011T220838.log`、`packaged_flow_20261011T220857.log`。审计复制当前 Editor/独立包六份 JSON 到 `Saved/V03/Regression/`。
- UAT：`Saved/CppMigration/20260929T083920372566Z/v03-package_20261011T140432483992Z.log`；其他编译、资产及失败日志保留在同目录和 `Saved/V03/Runs/`。

## 修复记录、恢复与后续人工测试

实际测试修复了材质在 NullRHI 生成后未预热造成的默认材质显示、箱体导航绕行、旧奖励文案与结算层遮挡、红光强度。合成输入时序和 PrePhysics 提前读取 Timer 结果导致的驱动误报已修正；所有失败尝试保留，不把失败运行计入通过证据。

完整恢复点：`Saved/V03/Checkpoint_20261011T205858/`；T23 源码检查点及各次 `T21/T22/T24/T25...Before_*` 资产备份保留。项目没有 Git，本轮未删除历史包/日志。Legacy 地图与保护资产一致性由最终审计核对；仅菜单指南为本轮预期更新。

人工仍须核对真实菜单/设置保存/退出、实体 WASD/鼠标/Q/E/1/2/R、三房路线与追逐手感、静音可读性和各事件听感，并记录真实保守/贪婪/随机试玩节奏。当前无主动丢弃、枪械射击、长期存档、商店、联网或 Shipping；满格仍可返回撤离，不构成流程阻断。下一步由用户人工试玩本发布候选，反馈后再针对性修正。
