# T42 工程阶段报告


Engineering Verified / Awaiting Human Validation。2026-10-15T18:31:08.878615+08:00。真人样本0，未标记HumanAccepted。

完整 Win64 Development 包（与测试候选全量SHA一致的新目录，不带自动化设置/存档）：F:/AnomalyLab/AnomalyLab_v05/Builds/v0.5/AnomalyLab_v05_RC_20261015T151040_Verified/Windows/AnomalyLab.exe。保持整个 Windows 目录，正常双击 AnomalyLab.exe；默认菜单进入独立安全基地 L_Hub，出发进入独立探索 L_Lab。

T35–T42分别执行实现、编译/适当自动化、新功能与相关旧回归、报告和SHA恢复点。T35跨场景结算/存档；T36共享购买权威；T37动态合法点位与独立RNG；T38配电；T39收容舱；T40两类有实际效果的环境事件；T41统计/加载反馈/步行流程；T42完整包验证与恢复归档。逐阶段报告及恢复索引见T35_REPORT.md至T42_REPORT.md、Saved/V05/checkpoint_Txx_verified.json。

T42首候选暴露A6旧掉落偏移被标本架遮挡。v0.5新增可配置掉落位置的球体/视线校验及有限站位回退，并在生成时复核；旧图偏移和奖励RNG不变。加强后的20局713断言逐局执行真实E拾取与实际价值结算；源预检及最终包完整矩阵均通过。首候选和失败日志保留。

额外边界回归覆盖：已携带物品时发生关卡技术错误，战报准确记录损失且不增加永久余额；独立Error分支与保存写入故障分别测试。第二候选的矩阵因补充这条源代码修复而明确标记INTERRUPTED，已有证据保留；最终候选完整重测。

包内矩阵：F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T42\Matrix_20261015T153730\report.json。共30个顺序任务，覆盖新玩法、20次地图往返、多点合法性、交易/异常/去重、跨进程重启、携带未兑现/已兑现尚未回Hub两种真实OS强制中断、正常启动旧档导入、720p/1080p实际D3D12画面、全部11组旧回归和Legacy。测试夹具、NullRHI与渲染模式均保留在原始命令/日志；自动输入和截图审阅不作为真人证据。

恢复验证：F:/AnomalyLab/AnomalyLab_v05/Saved/V05/T42/Restore_20261015T182518/report.json。全量源工程1494文件及完整包48文件复制到新目录后SHA复读，通过恢复源Editor Hub启动与恢复包三次步行往返。未在恢复目录重新编译；源恢复重建需UE5.8和新的ASCII构建上下文。

代理画面审阅：Saved/V05/T42/visual_review.json。加载盖层、菜单/商店、扫描/背包、成功/死亡战报、配电/警报及两个分辨率的真实帧已单独记录。最终听感、真实键鼠、公平性、自然局长与平衡由用户统一人工测试，使用HUMAN_TEST_GUIDE.md/PLAYTEST_RECORD.md。

T41及包内性能原始数据见Saved/V05/T41/telemetry_audit.json与Saved/V05/T42/telemetry_audit.json。FPS为20Hz抽样的引擎CPU帧间隔，包含加载/截图开销；不是GPU基准，不声称60FPS或3–5分钟真人目标达标。统计限20文件，事件/样本/文件大小有上限，可用-NoRunTelemetry关闭，不参与经济权威。

版本兼容：保留Schema2及原槽名，Progression为唯一永久经济管理者。导入仅对无主档/备份的新目标生效，源文件只读。不可读现有档阻止购买/出发；崩溃/退出不兑现携带物品，出发后已消费诱饵不退款。测试只用Automation_隔离槽，未导入任何玩家真实档。

基线：1081旧Content、原工程非文档载荷、已验收v0.4 RC和v0.3/v0.4归档SHA保持。原工程4份文档在外部维护中变化，固定路径+SHA例外证据Saved/V05/T35/external_baseline_document_changes.json；初始严格身份FAIL保留，未重设清单。本任务没有写入原工程/RC/归档。

完整恢复归档：F:/AnomalyLab/AnomalyLab_v05/Saved/Releases/v0.5_AnomalyLab_v05_RC_20261015T151040_HumanPending，含Project/、完整Package/Windows/、成功与失败Evidence/及release_manifest.json。最终归档SHA复读和T42恢复点状态以Saved/V05/T42/release_archive.json、delivery_summary.json、checkpoint_T42_verified.json为准。归档为同盘恢复副本。

已知边界与原失败保留见KNOWN_ISSUES.md；原有GameFeatures handled ensure未隐藏。任何人类验收结论需用户后续提供。

构建日志：F:\AnomalyLab\AnomalyLab_v05\Saved\CppMigration\V05_T34_20261013T190745\v05-rc-package_20261015T071046640733Z.log
源清单：F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T42\package_source_20261015T151040.json
包清单：F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T42\package_payload_20261015T151040.json
