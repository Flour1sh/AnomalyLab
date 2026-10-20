# T12 扫描构建

授权范围（2026-10-02）：仅 Python/C++ 构建资产和程序，不使用 UE MCP、屏幕接管、PIE 或玩法测试。T11E 已由用户验收；本阶段不提前实现 T13 三箱及后续 HP/撤离。

## 实现与资产

- `UAnomalyScannerComponent` 以相机中心 300 cm Visibility 射线经 `IAnomalyScanTarget` 读取目标；保持 Q 一秒完成当前仪器扫描。Q 松开、遮挡、切目标、切装备、E 开箱及无效阶段取消，取消后需重新按 Q。轮次由箱子的 `CanScan` 向现有 Coordinator 校验。
- `AAnomalyBoxActor` 按实例和仪器缓存确定性读数，读取已初始化的定义副本，不抽随机数、不改结果或钱包。重新对准恢复记录；新箱、新局自然得到空缓存。
- 金额按定义的下/上扩展系数向外取整到百元；威胁等级阈值 15%/30%，高价值等级阈值 35%/50%。未知隐藏配置按正负 10 个百分点扩展并裁剪。HUD 只收到已扫描标记、金额区间、模糊等级、可靠性，不接收内部箱型或精确概率。
- `/Game/Core/Components/BPC_Scanner`：原生扫描组件的 Blueprint 配置，范围 300 cm、时长 1 s、面板类引用；挂载于 `BP_FirstPersonCharacter.T12Scanner`。
- `/Game/UI/WBP_ScanPanel`：`UAnomalyScanWidget` 的基础中文面板，左侧当前箱子的三项汇总，准星下方进度，下方装备/操作提示。使用现有 HUD 的独立扩展层；无逐帧 UMG 属性绑定，展示变化才提交更新。
- 原有 `BP_FirstPersonCharacter` 是本次唯一需要修改的旧 uasset；原有 HUD、地图、箱子呈现、交互图和数据资产不重建。

## 重建

关闭使用项目模块的编辑器，在 `F:/AnomalyLab` 执行：

```powershell
python '我的项目3/Scripts/cpp_migration.py' build-editor
python '我的项目3/Scripts/cpp_migration.py' editor --script build_t12_assets.py --phase t12-build
python '我的项目3/Scripts/cpp_migration.py' editor --script verify_t12_assets.py --phase t12-reload
```

沿用 ASCII 副本编译、原工程部署。资产脚本进程使用 NullRHI，禁用 AllToolsets、ModelContextProtocol、MCPClientToolset，仅启用本地 EditorToolset/Python/UMG 编辑 API；没有 MCP 连接。脚本重建仅针对 T12 自有面板，每次先备份将改动的包。

备份：`Saved/T12/Backup_20261002T153356/` 保存修改前 Source/Docs；资产备份见 `Saved/T12/AssetBackup_*/`。构建/重载报告在 `Saved/T12/`；进程命令、失败和原始编译日志仍由 `cpp_migration.py` 追加到 `Saved/CppMigration/20260929T083920372566Z/`。

## 验收范围参考（构建时未执行；用户现已总体确认通过）

1. 三仪器各按 Q 一秒；松开、移开、遮挡、超过 300 cm、切仪器/枪应取消且从零重新开始；枪不能扫描。
2. 重新对准恢复已扫描项目；未扫描项不泄漏，重复扫描不改变读数。扫描中按 E 可以开箱；非 Ready、旧箱和已开箱拒绝扫描。
3. 检查六套实际配置、金额覆盖/百元取整、概率边界及可靠性。固定种子下对比未扫描/单次/多次/切仪器的开箱结果与收益序列。
4. 回归开箱、奖励、威胁、两次威胁结束与 R 重开；重开后扫描记录和进度清空。
5. 实景检查 1920×1080 与 1280×720 的面板/装备/原 HUD 不重叠、中文无缺字；实体 Q/E/1/2 输入与音画由后续测试确认。

构建和资产重载仅证明编译与引用；不代表 T12 玩法验收通过，也未更新独立打包版本。

## 本次构建结果

- 最终 Editor 编译成功：`build-editor_20261002T073947971132Z.log`，UBT `Result: Succeeded`，退出码 0，原工程 DLL/模块清单/Target 收据已部署。
- 资产生成成功：`Saved/T12/build_report.json`，退出码 0。两个新增 uasset 和玩家组件已保存。
- 独立进程重载成功：`Saved/T12/reload_report.json`，4 个 Blueprint 编译通过；核对唯一 Scanner/Equipment、300 cm/1 s/面板类、三个绑定控件和四个装备网格引用。
- 初次沙箱编译因 UnrealBuildTool 用户缓存权限失败，日志保留；获得执行权限后编译成功。首次成功编译中一个任务因内存压力被构建器重试，最终通过，未忽略编译错误。
- 未执行：PIE、数学边界运行测试、随机序列回归、实体输入、画面/音效、独立包构建与验收。


## 人工验收（2026-10-02）

用户反馈：“没问题，测试完成写入日志”。据此将 T12 标记为人工测试验收通过，下一阶段为 T13 多箱。以上清单保留为范围参考，不将用户总体确认展开为逐项测试结果；未提供自动测试或独立包报告，既有构建证据与未执行记录保持其原始边界。独立验收日志见 `Saved/T12/acceptance_log.md`。
