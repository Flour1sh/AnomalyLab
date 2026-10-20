# T33 基线审计与两关卡设计报告

时间：2026-10-13T18:40:24.385107+08:00。状态：T33 工程验证通过；本报告只有在 `Saved/V05/checkpoint_T33_verified.json` 为 PASS 时构成完整闭环。v0.5 游戏功能尚未实现，未打包。

## 工作副本和基线保护

独立工程 `F:/AnomalyLab/AnomalyLab_v05/我的项目3.uproject`。原工程 `F:/AnomalyLab/我的项目3`、v0.4 已人工验收 RC_20261013T131738、v0.4/v0.3 发布归档与原包保持原样。无 Git，采用完整 SHA 检查点。初始复制1407文件/1,638,949,825字节；未复制个人 SaveGames。归档清单2030项校验PASS；前后全树检查包含清单自身2031项。原副本8个文档变化为已有验收补记，Source/Config/Content/Binaries无偏差。

`Saved/V05/T33/protected_after.json`：原工程1407文件、v0.4归档2031、v0.4原包106、v0.3归档1871、v0.3原包53，文件集合与SHA全部一致。工作副本Source/Config/Content/uproject共1152项未改；8个旧测试入口脚本逐字未改。新增文件/编译产物见 `Saved/V05/T33/changed_files.json`。

## 真实实现和冻结方案

默认仍为独立L_MainMenu → L_Prototype内Preparation → 同图探索，R重载当前地图。新进程实际重载16项PASS：主菜单46Actor且无Coordinator，探索277Actor、一个Coordinator/PlayerStart/NavBounds/Recast；出生(0,1750,110)、yaw-90；Legacy44Actor且无Preparation/Region。新Hub/Lab尚未创建。

永久经济已有GameInstance ProgressionSubsystem；商店为Coordinator原生输入+WBP_ExplorationPrompt被动显示，Schema2 SaveGame持久化，成功物理入口次帧校验兑现，死亡优先。购买与BeginRun依赖旧Coordinator，新图不能直接套用。重要修复入口：关闭Lab Preparation会跳过Progression配置，必须显式初始化/claim并禁止Wallet-only假成功；R终局必须回Hub；旧存档损坏不可静默归零。

冻结：两个真实文件Content/Maps/L_Hub.umap与L_Lab.umap；Hub安全空间/商店/报告/出发，Lab保留ABC与物理撤离；既有Progression继续唯一经济权威，新增TransitionSubsystem只保存RunId/version/种子/装备值/结果DTO；出发消费诱饵一次，Lab接收一次；死亡/错误0兑现；结束先封口/快照/保存/清理，再回Hub；重启回Hub不恢复未兑现Loot、不重放记账。完整迁移表/平面/存档策略见ARCHITECTURE_MAP、LEVEL_DESIGN、SAVE_MIGRATION、DECISIONS。

## 编译和自动回归（真人样本0）

独立ASCII构建副本 `Saved/BuildWork/V05_T33_Baseline`。编译MaxParallelActions2，39 actions，126.01秒，exit0。成功日志：`Saved/CppMigration/V05_T33_20261013T181946/build-editor_20261013T102620726164Z.log`。

| 组 | 复制RC | 重编译Editor源码 |
|---|---|---|
| resources | PASS / 10 | PASS / 10 |
| equipment | PASS / 29 | PASS / 29 |
| save | PASS / 26 | PASS / 26 |
| regions | PASS / 78 | PASS / 78 |
| observer | PASS / 32 | PASS / 32 |
| balance | PASS / 11 | 未重跑（T33复制RC已覆盖） |
| core | PASS / 172 | PASS / 172 |
| menu | PASS / 22 | PASS / 22 |
| legacy_stats | PASS / 52 | 未重跑（T33复制RC已覆盖） |
| legacy_decision | PASS / 47 | 未重跑（T33复制RC已覆盖） |
| legacy_flow | PASS / 66 | 未重跑（T33复制RC已覆盖） |

存档组每目标10个独立OS进程；表中数字为实际自动断言数。区域逻辑78与历史渲染81之差为3个额外截图检查。未删除/改写旧断言。源码汇总可审计最初失败与随后重跑；不是掩盖失败。

命令：`python Scripts/run_v05_baseline.py --target package`；`python Scripts/cpp_migration.py build-editor`；`python Scripts/cpp_migration.py editor --script audit_v05_baseline_assets.py --phase v05_t33_audit`；`python Scripts/run_v05_baseline.py --target editor --groups resources equipment save regions observer core menu`（渲染因权限中断后，resources既有PASS保留，其余6组以相同断言重跑）。包装矩阵 `Saved/V05/T33/Regression_package_20261013T182018/report.json`；源码实际报告见 `Saved/V05/T33/source_regression_summary.json`。

失败记录保留：初始同级构建目录写权限；沙箱UBT用户trace轮换失败；首次Editor装备渲染无法写用户UnrealShaderWorkingDir导致无report，判FAIL。授权构建/渲染重跑后通过，未改源码来适应权限问题。

真实720p D3D12离屏图已生成；代理查看商店/入口/同帧死亡帧，见visual_review.json。自动输入路由/渲染不等于真人物理按键、听感或5人×3局。新地图、三次往返、1080p新流程和新存档迁移待后续阶段，不宣称完成。

## 闭环和下一阶段

文档：ARCHITECTURE_MAP、LEVEL_DESIGN、SAVE_MIGRATION、DECISIONS、KNOWN_ISSUES、TEST_MATRIX、PLAYTEST_RECORD、progress、本报告；计划精确复制到Docs。新脚本bootstrap_v05、run_v05_baseline、audit_v05_baseline_assets、checkpoint_v05、finalize_v05_t33；旧玩法源码/地图/配置不变，Editor产品重新编译。

完整恢复点索引 `Saved/V05/checkpoint_T33_verified.json`，逐文件SHA重新读回；恢复到NEW目录并新建ASCII编译上下文，勿覆盖旧工程。检查点不含个人档/缓存/测试包，证据保留工作副本Saved。T33遵循计划§13.2/§14，本会话只做该阶段。下一任务T34：按冻结设计生成并独立重载真实Hub/Lab，测出生/碰撞/导航/视觉并回归；T35–T41依次完成后才T42打包。无新v0.5包，无新Human Accepted标记。
