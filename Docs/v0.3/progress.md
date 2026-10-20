# 最新状态：场景细节版人工测试完成并保留（2026-10-11）

用户已总体确认基础 v0.3 人工测试完成，随后授权按一致风格生成模型并打磨场景；不补造逐项人工结果。新美术版模型/关卡/Win64 构建 DONE，完整实际渲染玩法 151/151、UE 独立重载 53/53、FBX 12/12、交付审计 149/149 PASS。新增 12 网格/13 材质，1,045 个旧资产、Source/Config 未变。

用户随后反馈：“测试完成，你可以保留一下这一版然后记录工作报告了”。本次新美术版已获总体人工测试完成确认，未提供逐项人工记录，不补造测试明细。

已验收包：`Builds/v0.3/AnomalyLab_RC_20261011T225958/Windows/AnomalyLab.exe`。工作报告 `Docs/V03_WORK_REPORT_2026-10-11.md`，场景明细 `SCENE_POLISH.md`，生成说明 `ScenePolishAssets/README_GENERATION.md`。验收后完整源码/资产、独立包与证据归档在 `Saved/Releases/v0.3_ScenePolish_Accepted_20261011/`，附恢复说明和哈希清单。本轮继续仅后台 Python/命令行，不调用 UE MCP 或接管屏幕。

---

以下为升级前基础版交付记录；表中人工待测状态保留为当时事实，已由后续用户总体确认补充，不据此伪造逐项验收。

# AnomalyLab v0.3 进度

更新：2026-10-11。当前范围：用户授权完成全部 v0.3 并自行自动化测试，人工试玩随后由用户执行。仅用本地 Python/C++、UE 命令行构建与后台运行；未调用 UE MCP、未接管屏幕、未修改扩展配置。

## 当前交付状态

| 阶段 | 实现 | 自动化 | 人工验收 |
|---|---|---|---|
| T19 菜单 | DONE | 最终包两档各 21/21 PASS | PENDING_MANUAL |
| T20 探索空间 | DONE | 资产/导航/实际步行路线 PASS | PENDING_MANUAL |
| T21 实体 Loot | DONE | 固定价值、一次生成/领取、距离/遮挡/身份 PASS | PENDING_MANUAL |
| T22 四格背包 | DONE | 0–4/满格/连按 E/跨轮/重开 PASS | PENDING_MANUAL |
| T23 风险与兑现 | DONE | 物理入口、死亡损失、同帧死亡、空包、二次收容、迟到回调 PASS | PENDING_MANUAL |
| T24 音画 | DONE | 720p/1080p 静音实际渲染 PASS | PENDING_MANUAL |
| T25 候选交付 | DONE | 最终包双分辨率各 151/151；审计 267/267 PASS | PENDING_MANUAL |

当前包：`Builds/v0.3/AnomalyLab_RC_20261011T220432/Windows/AnomalyLab.exe`。完整结论与证据位置见 `FINAL_REPORT.md`；人工清单与全部重跑命令见 `../../Scripts/RUN_V03.md`。原来的 T19 独立包、T20 构建当时无背包/撤离的记录均为历史，不能描述当前版本。

## 本轮变更与验证

- 新建 C++ ItemDefinition、WorldPickup、Inventory、V03Smoke；扩展 Coordinator/Box/Scanner/Threat/ExplorationWidget/DecisionWidget/MenuSmoke。精确契约与资产路径同步 `Docs/01_CONTRACTS.md`、`Docs/ASSET_MAP.md`。
- Python 生成四种物品定义/网格/材质与九种 SoundWave，更新探索 HUD、菜单指南与地图实例引用。`Saved/V03/T21_assets.json`、`T22_assets.json`、`T24_assets.json`、`ui_polish.json` PASS。
- 编译 Editor、保存资产、独立重载 36/36、D3D12 材质预热 12 项 PASS。未保存强制开奖、固定随机种子或故障注入到生产资产。
- 连续流程从真实默认菜单进入：扫描、拾取、满格、继续、携带处理自然威胁、实际返程兑现、结算、R；Editor 逻辑 146/146，最终包 720p/1080p 渲染各 151/151，菜单启动各另 3/3，共 48 张玩法/菜单截图。
- Legacy Editor 和最终包各 stats 52/52、decision 47/47、flow 66/66 PASS。旧三箱随机/扫描/直接奖励/追逐/终局行为兼容。
- 保守/贪婪/随机机器人各 1 次真实导航/扫描/非强制开奖样本 PASS；样本不足以推断人类死亡率、操作体验或 3–5 分钟节奏。
- Win64 最终包 UAT 成功，最终审计 267/267 PASS：86 份 Source/Config/关键资产、构建副本、最终二进制和截图尺寸一致，Legacy/106 个保护资产哈希未变，项目插件配置未改。
- 实测修复：NullRHI 生成材质的着色器预热、探索箱动态导航阻挡、结算底板/提示底板和红光强度。合成输入先后顺序、Timer 与 PrePhysics 断言时机等测试误报已修正。
- 原始失败、候选包和截图全部保留，不以最终成功覆盖失败。全量备份 `Saved/V03/Checkpoint_20261011T205858/`；T23 源码及每次资产生成另有检查点。

## 历史与后续

- T19 菜单历史说明：`T19_MAIN_MENU.md`。用户对旧基线审计的确认，不等于新增菜单已经人工验收。
- T20 阶段审计/空间构建：`00_baseline_audit.md`、`T20_EXPLORATION.md`；其中“未进入 T21/等待 MCP”的记录是当时范围，已由本次用户新授权继续全版本实施。
- 迁移/v0.2 历史：`Docs/CPP_MIGRATION.md`、`Docs/V02_WORK_REPORT_2026-10-07.md`；当前事实以 `Docs/STATE.md` 与 `FINAL_REPORT.md` 为准。
- 下一步：用户人工试玩当前 RC，核对实体输入、菜单设置与退出、听感/静音可读性、路线/追逐和三策略节奏；记录反馈后再修正。当前不新增丢弃/射击/存档/商店/联网/Shipping。
