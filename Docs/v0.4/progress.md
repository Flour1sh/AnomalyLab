# v0.4 Progress

Current Task: T32
Baseline RC: RC_20261011T225958
Status: Implemented / Automated Verified / Visual Verified / Human Accepted (user confirmation)
Updated: 2026-10-13T14:51:45+08:00

## 用户人工验收通过
- 用户原文：“人工验收通过，写入日志”。对应最新RC AnomalyLab_v04_RC_20261013T131738，已记录总体人工验收通过；详细见ACCEPTANCE_LOG.md。
- 人数、局数、逐项指标和视频未提供，不补造样本，也不宣称5人×3局已完成。本次只更新文档与独立验收索引，原发布程序/归档/SHA保持原样。

## 最终工程交付
- T27–T31按依赖完成并逐阶段保存SHA恢复点；T32最终包 `Builds/v0.4/AnomalyLab_v04_RC_20261013T131738`。
- 最终矩阵17/17组PASS，菜单两档各22、核心各172+3、观察者各32、区域各81、保存10进程/26项、曲线11、Legacy52/47/66；详细 `Saved/V04/T32/Matrix_20261013T132652744204/report.json`。
- 恢复演练1452文件SHA、迁移包冷启动/资源通过。最终归档与恢复点成功索引：Saved/V04/T32/release_archive.json、Saved/V04/checkpoint_T32_rc_verified.json。
- 当前不再新增功能；用户已确认总体人工验收通过，详细试玩统计未提供。PLAYTEST_RECORD保留可选补充字段和工程交付时的历史记录。
- 断点中审批服务额度拒绝已在2026-10-13恢复；失败与修复见T32_REPORT，旧证据保持。

用户最新指令已授权本轮完成 T27–T32，仍逐任务 PLAN → IMPLEMENT → VERIFY → REPORT → CHECKPOINT。T26 用户总体验收已通过，不补造人数、局数或逐项反馈。以下历史记录保留。

## 2026-10-13 T32 断点恢复
- 审批服务额度拒绝导致的中断已恢复；独立菜单重载14项PASS，720p/1080p菜单各22项PASS。修正旧验证脚本对控件名、文案和移动冻结方式的错误假设，未更改生产玩法。
- 初始候选15组矩阵及1449文件恢复演练通过，视觉复查发现旧版本菜单文案后生成新候选；当前完整Win64构建进行中。新包将执行17组矩阵及新目录恢复验证后归档。
- 0人0局；人工听感/公平性/节奏待测，交付Human Pending RC。

## 2026-10-12 T31 阶段完成
- 新可检查有界曲线、真实轮次HUD与48格24万局配置仿真。首轮T26摘要不变，来源/前后/模型假设/实际0真人/3–5分钟待测见BALANCE_CONFIG.md。
- 最终编译PASS；重载11/11、仿真边界11/11+摘要对照、原追逐者完整172/172+菜单3/3、观察者32/32、区域78/78。最终三种机器人14/21/21通过，非真人样本。
- 失败机器人路径、修复与复跑完整记录T31_REPORT；当前没有生产回归失败。恢复索引 Saved/V04/checkpoint_T31_verified.json。
- 下一步T32完整Win64 Development包、Editor/包矩阵、冷启动、发布归档/校验与恢复。

## 2026-10-12 T30 阶段完成
- 原生观察者、独立类型随机流、可配置视线迟滞/宽限/耐受、青/红眼与中文反制提示；详见 T30_REPORT.md。
- 最终编译、独立重载24/24、两档观察者各32/32、原追逐者完整路径172/172+菜单3/3、区域78/78、Legacy flow66/66 PASS。
- 实际查看两档眼部/红眼画面。首次渲染遮挡与无控制器重复日志已修复并复测；测试脚本控件名错误也已修正。
- 用户确认暂无真人样本，交付待人工验收RC；不将工程通过称为真人公平性验收。恢复索引 Saved/V04/checkpoint_T30_verified.json。

## 2026-10-12 T29 阶段完成
- 计划/接口/改动/脚本参数失败与证据见 T29_REPORT.md；版本化 USaveGame、隔离槽、事务保存、备份恢复、不可变终局快照已实现。
- 编译 PASS；10 个独立进程保存断言 26 项全部通过，持久化后的真实输入装备 29/29，完整路径 172/172 + 菜单 3/3，区域 78/78，Legacy flow 66/66。
- 实际查看存档状态、成功/死亡永久余额快照；测试资金与槽隔离，所有槽族已清理。真人体验待测。
- 恢复索引 Saved/V04/checkpoint_T29_verified.json；校验通过后进入 T30。存档 Schema=2，初始币 0，未来版本禁止覆盖。

## 2026-10-12 T28 阶段完成
- 计划、实际改动、接口、失败修复与证据见 T28_REPORT.md。四商品、明确局外整备、五格背包、有限精度和真实诱饵已实现。
- 最终编译 PASS；两档原生/实际输入效果各 29/29、资产重载 22/22、原有完整路径 162/162 + 菜单 3/3、区域 78/78、Legacy 52/47/66。
- 已查看两档商店/余额不足/购买结果/第五格真实渲染；真人体验待测。
- 恢复索引 Saved/V04/checkpoint_T28_verified.json；校验通过后进入 T29。T28 内存 Meta 未持久化，T29 负责扩展原子保存。

## 2026-10-12 T27 阶段完成
- 实现/文件/接口/失败原因/命令与证据见 T27_REPORT.md。扫描默认每种 3 次，仅成功首次读数扣费；Legacy 不限。
- 最终编译 PASS；资源边界 10/10，区域 78/78，720p/1080p 菜单全流程各 155/155 + 菜单 3/3，Legacy flow 66/66。
- 两档真实画面已查看，中文剩余次数与可靠性独立显示；真人体验仍待测。
- 回退索引 Saved/V04/checkpoint_T27_verified.json；下一阶段 T28，严格在恢复点通过校验后开始。

## This iteration
- 已读取根目录实施计划（用户提供的 Docs 路径不存在）、STATE、01_CONTRACTS、00_RULES、RUN_V03 与实际源码。
- 无 Git，使用独立版本快照与 SHA-256；验收归档不作为开发目录。
- v0.3 归档 1,869 文件 / 2,672,233,343 字节校验通过；旧 verify 脚本重写了归档中可重写的 verification_report.json，仅此报告时间更新，清单覆盖文件全部一致。后续只读检查结果保存至 Saved/V04。
- 首次受限环境运行 UE 未生成日志/报告，exit=0 不算通过；已在获准环境复跑。原始失败证据保留。
- Tests / visual / changes / final checkpoint: 本阶段完成时追加。
- 下一步：确认实际资产六配置与地图实例，复跑 v0.3 核心测试，再实现 T26。

## 2026-10-12 初始化完成 / T26 已实现，验证中

- 初始化：实际资产六配置与 t11_data.py 的概率/范围一致；入口和点位已存 asset_audit.json。v0.3 核心 146/146；Legacy stats 52/52、decision 47/47、flow 66/66 PASS。源代码编译前无运行 UE。
- T26 C++：RegionDefinition 数据校验/加权/归一化/三箱修复；Box 初始化副本/隐藏配置/上下文；Coordinator 区域映射/独立种子/只读提示/区域统计；ExplorationWidget 可选 RegionText。Legacy 采样不消费额外随机数。
- T26 资产：新增 DA_Region_A/B/C，修改仅 L_Prototype 与 WBP_ExplorationPrompt；其余 1,070 Content 文件哈希未变，单独资产前备份 AssetsBefore_20261012T075902087073。
- Editor 编译两次 PASS；独立 UE 重载 43/43；原生逻辑 78/78；D3D12 720p、1080p 各 81/81，与逻辑统计完整签名精确一致。720p 三房中文已查看无截断；1080p 待查看。
- 固定种子每区域实际 60,000 样本：均值 A 812.624±11.620，B 1463.664±16.354，C 1911.686±20.216；威胁率 11.3017%±0.2533pp / 24.6200%±0.3447pp / 34.5583%±0.3805pp（95%）。仅生成面值/威胁，不是撤离收益/死亡率。
- 证据：Saved/V04/T26/assets.json、reload.json、Runs/20261012T075934391088_editor_logic_1280x720、Runs/20261012T080027906979_editor_render_1280x720、Runs/20261012T080116418599_editor_render_1920x1080。
- 当前剩余：修改后的核心回归、独立包/同种子对照、Legacy 回归、最终只读审计与恢复点。T27 未开始。

## 2026-10-12 跨目标测试修复（非玩法变更）

- 初包 Win64 构建成功且内部 81/81，通过后严格 JSON 对照失败；原始报告和 cross_target_failure.json 在 Runs/20261012T080744942157_package_render_1280x720。
- 五个浮点末位差异（均值/方差/区间/归一化概率，约 1 ULP）；离散计数、种子、金额和缓存均相同。增加全 180,000 采样的离散序列摘要，所有离散字段仍严格一致；派生浮点仅允许 1e-12 相对/绝对误差，不修改生产玩法。
- 测试修复 Editor 编译 PASS；78/78 复跑，摘要 3e7cb1abde8dd2c2；报告 Runs/20261012T081009830509_editor_logic_1280x720。重打独立包中。
- 最终玩法模块 Legacy Editor stats/decision/flow 再次 52/47/66 PASS，日志分别 080743 / 080757 / 080826。1080p 三房区域截图也已查看，无截断。

## T26 final checkpoint / 2026-10-12 08:18

- 完成：初始化实际结构/契约/资源/资产审计，三份区域 PrimaryDataAsset、概率修正/Unknown 保留、中文提示、可分区遥测、固定种子统计与全部阶段工程检查。
- 修改文件：Source 新增 RegionDefinition.h/.cpp、RegionSmoke.cpp；扩展 Box.h/.cpp、RoundCoordinator.h/.cpp、ExplorationWidget.h/.cpp、AnomalyLab.cpp。Content 新增三个区域资产，仅修改原探索地图/HUD。脚本/文档详细清单见 Saved/V04/T26/delivery_audit.json 和 T26_REPORT.md。
- 契约：不改选一锁二、扫描时长/距离/遮挡/缓存、四格背包/跨轮携带、手动入口撤离/死亡优先、追逐参数/两次收容强制返程及 Legacy。新增区域数据只读副本；Wallet 不承载新经济。
- 最终构建：Builds/v0.4/AnomalyLab_T26_20261012T081026/Windows/AnomalyLab.exe。完整 Win64 目录已保留；首包未删除。
- Tests: Editor 编译（最终测试修复含摘要）PASS；独立重载 43/43；原生统计 78/78；Editor/包两档区域实景各 81/81，全 180,000 采样离散摘要均 3e7cb1abde8dd2c2。派生浮点 1e-12 容限内差异单独记录，绝不放宽离散开奖/金额。
- v0.3 回归：初始化/修改后 Editor 核心各 146/146；最终包 720p/1080p 静音完整实景各 151/151，默认菜单另各 3/3；Editor/包 Legacy 各 52/47/66。原自动输入/临时分支设置，不是人类实体键鼠。
- Visual: Editor/包三房两档共 12 张区域截图已查看；最终包两档各 18 张核心截图，已查看入口/扫描/预警/撤离/死亡代表画面；中文区域提示不截断、终局无区域层残留。其余截图作为原始证据保留，未声称每张均由真人审核。
- Audit: 9/9 PASS；v0.3 归档清单 1,869 文件未变、初始化 1,124 源/资产对齐、1,070 非目标 Content 和全部 Config 未改、1,130 打包源与当前/ASCII 副本一致；48 份包文件 SHA-256。旧 verify 更新派生报告时间的事实保留。
- 报告/复跑命令：Docs/v0.4/T26_REPORT.md、BALANCE_CONFIG.md、ACCEPTANCE_CHECKLIST.md、Scripts/RUN_V04_T26.md。不可变阶段结果副本 Saved/V04/T26/Regression/，汇总 regression_summary.json。
- 失败记录：首次受限 UE 无报告；首包浮点严格对照失败，均保留且未计为通过。详见 KNOWN_ISSUES。
- Rollback: 初始化 Checkpoint_20261012T074812_initialization（1,279 文件）；T26 恢复索引 Saved/V04/checkpoint_T26_verified.json（仅在脚本完成逐文件 SHA-256 验证后写入）。恢复 Project 到新目录；不要叠加覆盖旧快照。
- Human: 0 位，键鼠、听感、玩家取舍体验 PENDING_HUMAN。新功能未获用户人工验收，不扩写 v0.3 的历史人工确认。
- Next smallest step: 用户按清单试玩本 T26 检查点并记录反馈；本轮停止。下一阶段 T27 依赖 T26，尚未开始，不连带实现 T28–T32。
