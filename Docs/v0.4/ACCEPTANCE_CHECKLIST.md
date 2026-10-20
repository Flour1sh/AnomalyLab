# v0.4 RC 验收清单

更新：2026-10-13T14:51:45+08:00。工程门槛通过，Human Accepted（用户总体确认）；人数、局数未提供。最终包 `Builds/v0.4/AnomalyLab_v04_RC_20261013T131738/Windows/`。用户原文与证据边界见ACCEPTANCE_LOG.md。

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

| 附加门槛 | 结果与证据 |
|---|---|
| Editor编译与独立资产重载 | PASS；T27–T31阶段报告、最终菜单14项重载 |
| 720p/1080p中文代表帧 | 已查看；菜单/指南/商店/扫描/五格/观察者/终局见T32_REPORT |
| 源/包一致、非目标Content保护 | delivery_audit.json逐文件SHA；仅14个目标Content，无删除，uproject扩展不变 |
| 迁移恢复包 | PASS；1452文件SHA、正常冷启动7、资源/装备29；源码未另编译 |
| v0.3清单只读复核 | 1869文件；最终结果见T32外置readonly_verify报告 |
| SHA发布归档 / 最终检查点 | 成功索引release_archive.json / checkpoint_T32_rc_verified.json；恢复到新目录 |
| 用户总体人工验收 | PASS；用户明确反馈“人工验收通过，写入日志” |
| 真人观察者测试/至少5人×3局 | 人数/局数与逐项记录未提供，不宣称该样本目标完成 |
| 3–5分钟、听感、扫描价值、定价 | 用户总体确认已记录；逐项指标未提供 |
| 完整真人视频或详细操作记录 | 未提供；PLAYTEST_RECORD.md保留未填写字段 |

人工按PLAYTEST_RECORD.md正常启动测试，保存实际日期/人数/版本/操作/问题；不得将仿真、机器人或截图计为人工证据。最终矩阵 `Saved/V04/T32/Matrix_20261013T132652744204/report.json`。
