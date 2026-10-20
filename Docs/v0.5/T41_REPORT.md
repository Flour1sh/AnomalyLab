# T41 工程阶段报告

完成时间：2026-10-15T14:10:46.077915+08:00。自动化门槛PASS；最终闭环以Saved/V05/checkpoint_T41_verified.json为PASS为准。

本阶段设计与改动见T41_PLAN.md及ARCHITECTURE_MAP/DECISIONS。永久经济仍为Progression/Schema2，本任务未修改v0.4原工程或旧Content。

| 验证 | 结果 | 证据 |
|---|---|---|
| Loop | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_Loop_20261015T135112455330\report.json |
| Direct | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_Direct_20261015T135136609483\report.json |
| Shop | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_Shop_20261015T135146101115\report.json |
| Placement | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_Placement_20261015T135214567942\report.json |
| Power | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_Power_20261015T135416362151\report.json |
| Chamber | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_Chamber_20261015T135453188495\report.json |
| Events | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_Events_20261015T135531333558\report.json |
| Quiet | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_Quiet_20261015T135705506953\report.json |
| Journey | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_Journey_20261015T135812719323\report.json |
| Import | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_Import_20261015T135940380254\report.json |
| Corrupt | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_Corrupt_20261015T135952446373\report.json |
| RestartWrite | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_RestartWrite_20261015T140004468531\report.json |
| RestartRead | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_RestartRead_20261015T140016438780\report.json |
| Journey1080 | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_Journey_20261015T140025122973\report.json |
| TelemetryDisabled | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Run_Loop_20261015T140157716914\report.json |
| TelemetryAudit | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\telemetry_audit.json |
| regression | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\Regression_editor_20261015T140221\report.json |
| ui_polish.json | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\ui_polish.json |
| environment_reload.json | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\environment_reload.json |
| telemetry_audit.json | PASS | F:\AnomalyLab\AnomalyLab_v05\Saved\V05\T41\telemetry_audit.json |

模块SHA：3588e8c702eeb5f8fbf11c665134c38a95394c45861aa07ed3e026d1a88be4fd。完整命令/日志/结果：F:/AnomalyLab/AnomalyLab_v05/Saved/V05/T41/Gate_20261015T135112/report.json。原1081 Content、原工程非文档载荷及RC/归档全集合SHA不变；原工程4份外部维护文档变化单独保留证据Saved/V05/T35/external_baseline_document_changes.json（严格原字节身份审计FAIL保留，未重设原清单）。隔离Automation_存档；真人样本0。本阶段未打包，统一人工输入/画面/听感/平衡测试待T42交付用户。失败记录保留，不覆写历史报告。

新增Telemetry、LoadingWidget和独立Journey输入驱动；生产默认菜单、W真实碰撞步行、商店四项购买、Q扫描、E开箱/实体拾取、物理返程和三次往返通过，无瞬移。初始币、安全奖励和致死分支为明示夹具，不能当作自然局长/平衡。商店初始空档文案及设备面朝向已修正。地图生成两次幂等、全新进程重载通过。

诊断文件限20、每文件≤450000字符、事件≤512、CPU帧样本≤12000，写临时文件后替换；关闭统计的同一经济测试仍PASS。扫描、箱位、事件和反制、伤害、收益/损失、出入时间与加载实际采集。原始指标Saved/V05/T41/telemetry_audit.json。

自动步行[1280, 720]：平均局内17.29秒，采样CPU平均FPS122.09、最大P95帧耗5.82ms，最大Lab加载1.334秒、Hub加载0.390秒。

自动步行[1920, 1080]：平均局内19.24秒，采样CPU平均FPS106.73、最大P95帧耗7.30ms，最大Lab加载1.296秒、Hub加载0.386秒。

以上为20Hz抽样的实际CPU帧间隔及短自动路线，含真实加载/截图开销，不是GPU基准或真人3–5分钟目标。真人听感、操作、公平性、设备使用倾向与5人×3局均待用户最终统一验证。
