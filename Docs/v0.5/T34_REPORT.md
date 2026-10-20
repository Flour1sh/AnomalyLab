# T34 两关卡地图与安全基地报告

更新：2026-10-14T16:22:29.902455+08:00。状态：**T34 地图与安全框架工程验证通过**；完整恢复闭环以 `Saved/V05/checkpoint_T34_verified.json` 为 PASS 为准。工作副本 `F:/AnomalyLab/AnomalyLab_v05`，UE5.8。v0.5 购买与正式 Hub↔Lab 游戏闭环仍待 T35/T36；没有打包或宣称人工验收。

## 交付与模块边界

真实独立地图 `Content/Maps/L_Hub.umap`（51 Actor，导航8 tile）和 `L_Lab.umap`（278 Actor，导航28 tile）。Hub约16×20米，独立安全 Character、PlayerController、GameMode、被动UMG与4种终端；无扫描/装备/HP/钱包组件，无 Coordinator/危险箱/追逐者/观察者，伤害为0。WASD/鼠标/跳跃已接入；实际W轴移动、300cm与遮挡判定、E查看/ESC恢复输入由自动测试验证，鼠标观察/跳跃的真人物理输入仍待验收。商店目录和整备概览读取既有 Progression/Config，只读；出发通道明确未开放，战报为空状态，不伪造购买或结果。

默认菜单开始按钮进入 Hub，保留原加载防连点与输入恢复。新菜单为独立WBP_MainMenu_V05副本，旧蓝图不变。旧菜单/核心断言仅通过显式Development参数 `-AnomalyLegacyMenuRoute` 验证兼容路由；新正常路由测试没有该参数。

Lab从已保存L_Prototype可追溯复制，保留ABC场景、原角色/HUD、扫描/装备和数据引用。出生点(0,1750,110)，yaw=-90，入口标为撤离气闸。新增 `bAwaitLevelLaunch` 默认false，只有新Lab为true：独立打开可勘察，但没有授权RunId，不生成箱、不消费诱饵、不购物、不兑现。此门控防止T35未接入时绕过经济初始化。旧图行为由11组回归确认。T35需以真实launch claim/DTO替换等待分支，接入冻结装备、返回结算及死亡回Hub；T36接入实际商店操作与报告。

新增源码模块为 `AnomalyHub.h/.cpp`、`AnomalyV05LevelSmoke.cpp`；现有Coordinator只增加默认关闭的门控，菜单路由单独改动，Progression只增加自动测试存档白名单，SaveGame Schema2不变。场景布局与UE构建分为 `t34_layout.py`、`build_v05_levels.py`；生成器仅写新图/Prototype/V05资产，版本2重复执行幂等。原1081个Content文件SHA全部不变。

## 验证与证据

最终C++编译PASS：`Saved/CppMigration/V05_T34_20261013T190745/build-editor_20261013T120027559644Z.log`。DLL SHA256：`1d817792ab81c2eec2e4f2d53f6b4d65273ba1b0bbef3bba4b1a71c706b2e5fd`。新图测试六个独立进程均使用这一DLL。

| 新地图检查 | 结果 |
|---|---|
| 版本2第二次生成幂等、新进程实际资产重载 | PASS / 31断言 |
| Hub 1280×720、1920×1080 | 各PASS / 43断言、5帧 |
| Lab 1280×720、1920×1080 | 各PASS / 20断言、5帧 |
| 正常菜单→Hub 两分辨率 | 各PASS / 6断言、2帧 |

运行断言共138，实际D3D12离屏截图24；代理逐帧查看了Hub全景/商店/整备/出发/战报空态、Lab入口/ABC/出口和菜单前后。中文未裁切，无黑屏/空Pawn/出生重叠；气闸标识重叠与等待HUD空背景已修正。图片、SHA及具体观察见 `Saved/V05/T34/visual_review.json`。这些是自动输入和代理截图复核；真人样本0，不等同真人键鼠或听感验收。

运行测试包括真实W轴移动、胶囊撞墙后停止、终端距离/临时阻挡拒绝、重复E、ESC恢复、Hub无危险输入/伤害/财务变化；Lab保存完整Nav路径到ABC/入口并验证拒绝未经授权的开局/购物/结算；菜单由实际StartButton委托进入Hub并卸载旧Widget。视角定位使用明确的测试夹具，未作为连续物理行走或正式往返证明。

旧版当前源码完整回归：`Saved/V05/T34/Regression_editor_20261014T160838/report.json`。

| 组 | 结果 | 自动断言 |
|---|---|---|
| resources | PASS | 10 |
| equipment | PASS | 29 |
| save | PASS | 26 |
| regions | PASS | 78 |
| observer | PASS | 32 |
| balance | PASS | 11 |
| core | PASS | 172 |
| menu | PASS | 22 |
| legacy_stats | PASS | 52 |
| legacy_decision | PASS | 47 |
| legacy_flow | PASS | 66 |

存档组含10个独立OS进程，26项检查；使用Automation_隔离槽并清理，未复制或操作个人存档。原断言保留，区域/平衡引用只读历史报告。

## 保留的失败与恢复

初始编译私有伤害字段/成员名冲突及生成器Python属性访问失败已修复并重跑。首次Hub墙阈值与实测1000cm墙面/34cm胶囊不符，改为实测边界和停止速度；E/ESC与CameraCache同帧断言改为经过真实输入帧后验证，增加实际遮挡拒绝，未强制成功。失败报告和日志均保留。

`Matrix_20261013T200231/report.json` 中生成/重载/六个新图测试PASS，但首次资源回归子进程exit1且runner.log为空，因此整份旧矩阵仍保留FAIL；不能确定终止原因，不能当作玩法失败或成功。恢复断点后独立重跑全部11组PASS。权威合并证据是 `Saved/V05/T34/verification_summary.json`，没有改写旧矩阵状态。

旧GameFeatures.GameFeatureData handled ensure在T33日志已存在，保留原配置并记录，不隐去。正式购买、三次Hub↔Lab、撤离/死亡/错误优先、重启恢复、旧档迁移、跨场景AI/音频清理及独立包检查仍待后续对应阶段。

## 基线保护、恢复与下一阶段

`Saved/V05/T34/protected_after.json` 全集合/SHA检查PASS：原工程1407文件、v0.4归档2031、v0.4已验收原包106、v0.3归档1871、v0.3原包53，均无新增/删除/改动。T33恢复点保持原样。T34新增/修改/删除清单见 `Saved/V05/T34/changed_files.json`；恢复点索引为 `Saved/V05/checkpoint_T34_verified.json`，包含源码/配置/Content/脚本/文档/Editor二进制/模型音频原文件并逐文件SHA复读验证。恢复必须到新目录，不覆盖原工程；同盘检查点不防磁盘损失。

复现命令：

```powershell
python Scripts/cpp_migration.py build-editor
python Scripts/verify_t34_matrix.py --regression
python Scripts/checkpoint_v05.py --task T34 --audit-protected
python Scripts/finalize_v05_t34.py
```

本次恢复复用未变DLL及新图已通过的结果，单独执行 `python Scripts/run_v05_baseline.py --target editor --task T34` 补全回归。finalize只校验已有证据、写报告并创建SHA恢复点，不替代编译/测试；必须先有代理截图复核记录。

下一任务为T35：跨Level路由、RunId/出发消费与claim、结算幂等、死亡返回、重启/异常恢复和旧档兼容。本轮不启动T35。所有阶段完成后才进行T42打包；独立包、返回战报真实结果截图和人工验收仍待完成。
