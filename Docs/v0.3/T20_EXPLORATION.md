# T20 小型可探索实验室（2026-10-11）

本轮仅做 Python/C++ 源码和资产构建，不调用 UE MCP、不接管屏幕、不运行 PIE/玩法/音画测试，不打独立包。T19 菜单人工验收仍为 PENDING_MANUAL；本轮按用户要求准备下一步构建，不补记菜单验收通过。

## 实现与边界

- 菜单仍进入 `/Game/Prototype/Maps/L_Prototype`（Level01）。地图为 5 个模块：绿色入口/返回区、中央走廊、蓝色 A 区、橙色 B 区、紫色 C 区。入口面向走廊；房间门牌、绿色返回线和门洞提供路线指引。
- 三个候选箱位置为 `(-1000,350,50)`、`(1000,350,50)`、`(0,-1100,50)` cm，由既有三个原生组件配置。箱型仍独立抽样并保证至少两类；选一锁二、扫描缓存、揭晓时开奖、RoundId 和有限重试保持原逻辑。
- `EAnomalyPlayMode` 原生默认 `LegacyPrototype`；只有探索地图实例指定 `Exploration`。探索模式使用现有 BPC_Interaction 的 E 路由，NativeInteract 额外验证玩家身份、相机中心 Visibility 射线和 300 cm 距离；没有第二套 E 监听。
- `WBP_ExplorationPrompt : UAnomalyExplorationWidget` 是被动提示层，展示当前箱子可操作提示和路线。输入、随机、金额和轮次均不由 Widget 管理。
- 探索模式的决策阶段保留移动，以便返回入口；同阶段仍不能开新箱，按 1 继续/2 撤离的既有规则有效。终局仍冻结移动。第二次收容后仍拒绝继续。
- 怪物生成使用探索模式专用相对偏移 `(0,-300,-3)`，三点均留在房间内。导航范围覆盖场景，Recast 设为 Dynamic；原生编辑器构建函数仅对非游戏 World 执行，实际生成导航并记录有效 tile 数。
- R 重开只改当前地图的获取和调用连线，保留原 Ended 门控；正常地图和旧原型地图各自重开。
- 本轮入口区域只是 T20 的空间标识，不提供免伤，也不接入物理撤离兑现。Wallet 仍按旧规则直接入账；实体 Loot、四格背包和撤离兑现分别留 T21、T22、T23。

## 文件与资产

源码：`AnomalyRoundCoordinator.h/.cpp`、`AnomalyBoxActor.h/.cpp`、新增 `AnomalyExplorationWidget.h/.cpp`。三个旧 Smoke 驱动仅将硬编码重载路径改为当前地图；原断言保留。Python Editor 回归入口默认 Legacy，`run_t18.py --map` 和 `cpp_migration.py --map` 支持显式选择；旧包默认仍走原地图，新包做 Legacy 回归时传 `/Game/Prototype/Maps/L_LegacyPrototype`。`DefaultGame.ini` 和打包脚本加入 Legacy Cook 范围，但本轮没有运行这些测试/打包操作。

资产：

```text
/Game/Prototype/Maps/L_Prototype                 探索场景（现有入口）
/Game/Prototype/Maps/L_LegacyPrototype           修改前场景副本
/Game/UI/WBP_ExplorationPrompt                  提示层
/Game/Prototype/Environment/T20/SM_LabModuleCube
/Game/Prototype/Environment/T20/M_Floor
/Game/Prototype/Environment/T20/M_Wall
/Game/Prototype/Environment/T20/M_Trim
/Game/Prototype/Environment/T20/M_Entry
/Game/Prototype/Environment/T20/M_Hall
/Game/Prototype/Environment/T20/M_A
/Game/Prototype/Environment/T20/M_B
/Game/Prototype/Environment/T20/M_C
/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter  仅 T06Restart 当前地图连线
```

既有低模家具通过新地图 Actor 引用，原网格不修改；家具碰撞使用明确的立方体阻挡体，避免依赖导入网格是否有简单碰撞。原菜单及箱子/Scanner/Wallet/Health/Threat/定义资产由哈希保护；具体数量和哈希以最终构建报告为准。

## 构建与恢复

在工程根目录运行：

```powershell
python Scripts/run_t20_build.py
# 分步：--step cpp / --step assets / --step reload
```

入口只执行 C++ Editor 构建、无窗口 UE Python 资产生成和独立进程资产重载，不含 gameplay、PIE 或打包模式。沿用 ASCII 构建副本解决中文路径 MSVC PCH 问题，编译后部署模块。进程禁用 AllToolsets、ModelContextProtocol、MCPClientToolset；只在本地 Python 中使用已有编辑器库，不连接 MCP，不修改扩展或工程插件配置。

源码/配置/文档检查点：`Saved/T20/Checkpoint_20261011T202718/`。每次资产生成前保存 `Saved/T20/AssetsBefore_*/Content/` 及 `sha256.json`；首次 `AssetsBefore_20261011T203832987462/` 保存修改前地图与角色。旧场景独立保存在 `L_LegacyPrototype`。恢复时关闭编辑器，按检查点复制 Source/Config 和对应资产备份，再编译 Editor 模块。

## 证据与待测

构建结果以 `Saved/T20/build_report.json`、`reload_report.json` 和 `build_driver_*.json` 为准。原始 UE/UBT 日志在 `Saved/CppMigration/20260929T083920372566Z/`，完整命令在 journal.jsonl。

最终整链 `python Scripts/run_t20_build.py` 通过，报告 `build_driver_20261011T204928507358.json`：C++ Editor 编译成功，资产重复生成成功，独立重载/编译/结构检查 170/170。最终场景 92 个生成 Actor，28 个有效导航 tile，107 个保护资产哈希保持一致。Blueprint 最终编译状态为 BS_UpToDate（无警告）。

最终交付核对 `Saved/T20/delivery_manifest.json`：40 份 Source 文件与 ASCII 构建副本一致，2 份部署模块产品与构建产物一致；uproject 插件配置和总体计划原文保持原哈希。该清单同时列出本轮变更文件。

最终原始日志：`build-editor_20261011T124928898112Z.log`、`ue_build_t20_assets_20261011T124946580380Z.log`、`ue_verify_t20_assets_20261011T125009719574Z.log`。首次独立重载检查的出生点 -90° 严格浮点比较改为 0.001° 容差后通过；这是断言修正，不是改变实际出生方向。

首轮报告 `build_report_first_attempt.json` 已撤销为最终证据：日志发现 GetCurrentLevelName 执行引脚未接，以及导航的 AsyncLoadLock（0x20）导致 RebuildNavigation 跳过。后续构建补执行链、严格检查 Blueprint 编译状态，并在原生构建函数中 FlushAsyncLoading/FlushLevelStreaming 后生成导航、拒绝零 tile。失败尝试全部保留。

| 分类 | 本轮状态 |
|---|---|
| C++ 编译 / 保存 / 重载 / 结构检查 | 编译与重复生成通过；重载/结构 170/170 |
| 正常输入找三箱、扫描、选一锁二 | NOT RUN |
| NavMesh 可见覆盖、走门洞、怪物生成与追逐 | NOT RUN |
| 返回入口、决策、第二次收容后限制、R 重开 | NOT RUN |
| T11–T18 Legacy 玩法回归 | NOT RUN（旧地图/默认模式保留） |
| 中文、画面、音效、两档分辨率 | NOT RUN |
| 人工真实操作 | PENDING_MANUAL |

当前 T19 独立包仍是 T19 的历史构建，不含 T20。下一步仅为用户开启 UE MCP 后测试 T20 的空间、碰撞、导航与三箱交互，再决定进入 T21。
