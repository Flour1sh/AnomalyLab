# T32 发布候选工程验收与归档

## 最新人工验收确认 / 2026-10-13

用户明确反馈：“人工验收通过，写入日志”。对应最终RC AnomalyLab_v04_RC_20261013T131738，当前状态Human Accepted（用户总体确认）；详见ACCEPTANCE_LOG.md。未提供人数/局数/逐项指标，不补造样本。下面保留工程交付过程中的Human Pending历史；本次只更新文档，发布程序、原归档与原SHA不改，独立验收索引Saved/V04/accepted_release.json。

## PLAN（T31 checkpoint 20261012T095027 / 1338 文件 SHA PASS 后开始）
- 交付状态：Implemented / Automated Verified / Visual Verified / Human Pending。用户已明确先交付待人工验收RC，实际0人0局；无人工视频或已执行人工完整记录时明确列为缺项，不伪造。
- 精确改动：DefaultGame.ini版本元数据；新增 package_v04_rc.py / verify_v04_rc.py / cold_boot_v04.py / archive_v04_rc.py；发布文档与清单。无新增玩法功能。
- UAT Win64 Development 完整三地图cook/stage/pak/iostore/archive；源清单SHA与ASCII构建副本一致，旧包与v0.3归档保持。
- 最终包矩阵：两档菜单/原追逐者全流程，资源/真实装备与五格，10进程保存/坏档/Schema/失败，观察者两档，区域两档严格首轮对照，24万局曲线跨目标摘要，Legacy stats/decision/flow。
- 正常冷启动：无自动化驱动参数，默认菜单、正常本地槽、无测试日志，使用UE内建-seconds=12退出以保留exit=0证据；仅菜单，不消费/覆盖玩家存档。
- 实际查看两档菜单/商店/扫描/五格/观察者/撤离/死亡代表帧，逐项列出已查看与待人类确认。
- 归档完整Project制作源/最终Windows/最终矩阵日志与截图，SHA清单；只读验证v0.3清单；恢复NEW目录并验证副本哈希，运行恢复包测试，保留恢复报告。只读verify输出写到Saved/V04，不改归档。
- 更新FINAL_REPORT、ACCEPTANCE_CHECKLIST、BALANCE_CONFIG、progress、KNOWN_ISSUES、STATE与变更列表，完成后保留最终恢复点。

## IMPLEMENT / 首个候选构建（历史结果）
- 完整 Win64 Development 三地图 UAT PASS，277.63秒：Builds/v0.4/AnomalyLab_v04_RC_20261012T095216/Windows/AnomalyLab.exe；源清单1151文件与ASCII构建副本一致。配置仅新增ProjectVersion=0.4.0-rc1。
- 最终Editor1080p完整172/172+菜单3/3（Saved/V03/Runs/20261012T095242925418_render_1920x1080），十进程保存26项通过（Saved/V04/T32/editor_save_suite.json）。
- 只读v0.3归档1869文件/2672233343字节PASS（Saved/V04/T32/readonly_verify_20261012T0957*.json，实际名见目录），没有重写归档内报告。
- 差异审计1151打包源一致、1068原Content未改、uproject插件扩展配置未改；目标Content总13个，无删除。详细前后SHA见delivery_audit.json。

## 首轮跨目标验证失败与修复（非生产回归）
- Matrix_20261012T095754948621 中观察者/资源/装备原生report均PASS，但Python包装层在存档清理校验拒绝包内Saved目录。此Development包实际保存到Windows/AnomalyLab/Saved/SaveGames，而不是仅用户/工程目录。
- test_save_slots.py仅增加从明确EXE推导的包内SaveGames白名单；EXE必须是当前工作区内真实AnomalyLab.exe；仍只清理该次记录的Automation_<唯一槽>.sav族，不接受任意报告目录、不清玩家默认槽。全部相关runner传EXE；19个失败遗留文件按报告确切槽清理，记录failed_run_slot_cleanup.json。
- 包的运行时Saved属于存档/配置，不是发行payload；完整payload SHA排除此一个运行时子树，归档/恢复也不携带个人或测试Saved。冷启动同时校验包内/用户/工程默认存档字节不变。
- 首轮两档core172、区域81、曲线11、Legacy52/47/66和冷启动7均PASS；首轮不计全矩阵通过。首个恢复副本的资源包装层同样失败，保留RestoreValidation_20261012T095819日志。
- 修正后完整矩阵与新恢复副本复跑中；没有修改游戏二进制、概率或C++来迁就检查。
Status: Implemented / Final RC verification in progress / Human Pending。


## 断点恢复 / 最终 VERIFY、REPORT、CHECKPOINT（2026-10-13T13:32:30.370350+08:00）
- 初始候选修复清理路径后Matrix_20261012T100240350117共15/15通过，恢复1449文件通过；随后代表帧发现菜单仍显示v0.3，未将该候选作为最终交付。
- 仅更新WBP_MainMenu版本与指南文案/指南规则框高度，保持按钮/布局/引用。第二次生成Menu_20261012T101007638836通过；第一次重载因默认次数文案未重新生成失败，日志保留。
- 2026-10-12后续运行被自动审批服务额度拒绝，未执行；2026-10-13恢复。复验发现脚本MainPanel实际应为MenuDesign，旧文案匹配“箱子”需核对“开箱”和有限扫描提示；准备阶段实际用DisableMovement/MOVE_None而非IgnoreMoveInput。只修正测试，未改玩法来迁就测试。
- 最终Editor编译、菜单独立重载14项、独立菜单两档各22项通过；真实Slate菜单、准备状态、E启动3箱、恢复Walking、返回菜单均验证。
- 重新完整UAT最终包 `Builds/v0.4/AnomalyLab_v04_RC_20261013T131738` PASS；源清单1151文件。最终矩阵17/17组PASS：`Saved/V04/T32/Matrix_20261013T132652744204/report.json`，完整发行payload SHA不变。

| 最终包验证组 | 状态 | 检查数/范围 |
|---|---|---|
| balance | PASS | 11 |
| cold_boot | PASS | 7 |
| core_1080 | PASS | 172 |
| core_720 | PASS | 172 |
| equipment_1080 | PASS | 29 |
| equipment_720 | PASS | 29 |
| legacy_decision | PASS | 47 |
| legacy_flow | PASS | 66 |
| legacy_stats | PASS | 52 |
| menu_1080 | PASS | 22 |
| menu_720 | PASS | 22 |
| observer_1080 | PASS | 32 |
| observer_720 | PASS | 32 |
| regions_1080 | PASS | 81 |
| regions_720 | PASS | 81 |
| resources | PASS | 10 |
| save_suite | PASS | 10进程 / 26项 |

- 新目录恢复 `Saved/V04/T32/RestoreValidation_20261013T132647`，1452文件SHA、迁移包冷启动7/资源装备29 PASS，恢复源码未另编译。copy_manifest及运行日志纳入归档证据。
- Matrix_20261013T132043485221的17组功能均PASS，但总SHA门槛因首次启动新增Engine/Saved/Config/Windows/Manifest.ini而FAIL。已读取UE5.8 ConfigManifest.cpp确认是自动生成的版本2配置迁移索引；只将此确切文件和原AnomalyLab/Saved运行目录排除，其余48个发行文件仍逐一SHA。未改二进制或资产，使用同一最终包重新执行全部17组与迁移恢复，不把失败总报告改写成PASS。
- 已查看最终包11张代表帧，确切路径及范围见Saved/V04/T32/visual_review.json。中文指南两档无截断；扫描、五格、红眼、成功和死亡终局可读。05_preparation因E同帧实际捕获启动过渡，01_shop_owned实际是余额不足状态，不按文件名虚报内容；整备视觉以实际T28商店帧为准，状态与购买效果另有原生断言。
- 最终交付审计/只读v0.3校验/归档SHA的实际结果以Saved/V04/T32/delivery_audit.json、readonly_verify_*.json、release_archive.json为准，最终阶段检查点索引Saved/V04/checkpoint_T32_rc_verified.json仅成功后生成。
- 最终差异审计PASS：106个变更文件、1067个原Content哈希未改、仅14个目标Content、无删除、uproject扩展不变，1151个源文件与最终包源清单一致。v0.3只读清单1869文件PASS（readonly_verify_20261013T131933.json）。
- 各阶段恢复索引T27_verified、T28_verified、T29_verified、T30_verified、T31_verified均已有PASS。最终快照复制到新目录恢复，禁止覆盖旧已验收目录。
- 最终状态：Implemented / Automated Verified / Visual Verified / Human Pending；0人0局，人工视频/完整记录、观察者公平性、3–5分钟、声音/实体键鼠仍待测。下一步按PLAYTEST_RECORD人工验收，不新增功能。
