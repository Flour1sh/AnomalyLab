# v0.4 最终 RC 报告

更新：2026-10-13T14:51:45+08:00。状态：**Implemented / Automated Verified / Visual Verified / Human Accepted（用户总体确认）**。用户反馈“人工验收通过，写入日志”，对应本报告最新RC；详见ACCEPTANCE_LOG.md。人数、局数及逐项指标未提供，不补造记录。工程RC交付时Human Pending/0人0局为历史状态。

## 可运行交付
- 完整 Windows 目录：`Builds/v0.4/AnomalyLab_v04_RC_20261013T131738/Windows/`；运行其中 `AnomalyLab.exe`，复制时保留整个目录。
- 默认菜单 → 开始游戏 → 局外整备；↑↓选择、Enter购买、E开局；Q按住1秒扫描，1/2切装备或回合决策，F诱饵，入口E兑现，终局R重开。
- UE5.8 / Win64 Development；三地图完整cook/stage/pak/iostore/archive通过。最终源清单 1151 文件与ASCII构建副本一致，日志 `Saved/CppMigration/20260929T083920372566Z/v04-rc-package_20261013T051800805778Z.log`。

## 实现结果
- T27：每种扫描仪默认3次，仅成功首次读数扣费，缓存免费，取消不扣费，新局重置、跨轮保留。
- T28：四商品价格1000/1500/2500/600，上限2/2/1/1；电池最高每种5次、精度最多减干扰50%、4→5格、一次性5秒/1200cm诱饵。观察者免疫诱饵。
- T29：初始永久币0；Schema2、校验/临时写入/上一完整备份、购买与兑现事务、不可变终局快照。死亡/Error/直接退出不兑现，未来Schema禁止覆盖。
- T30：独立类型随机流的观察者35%/追逐者65%混合池；正视停步、遮挡/背向追逐、迟滞与宽限、4秒累计耐受后1.25秒红眼。保留预警1秒、自然收容20秒、330速度、25伤害与1.5秒冷却。
- T31：威胁权重倍率每轮+0.03至1.15、奖励倍率+0.05至1.30；首轮精确保持T26。24万局明示假设仿真，不作为人类死亡率或定价依据。
- T32：中文指南与版本号更新，完整独立包双分辨率回归、正常冷启动、恢复演练、SHA归档。Legacy与原追逐者闭环保留，无删除资产。

## 验证证据
最终矩阵 **17/17组 PASS**，发行payload运行前后SHA不变：`Saved/V04/T32/Matrix_20261013T132652744204/report.json`。

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

原追逐者完整路径两档各172项，连续菜单启动另各3项；独立菜单两档各22项。资源/装备、保存故障、观察者、固定种子区域/曲线和Legacy均见上述报告，不把断言数相加当试玩人数。

区域18万次生产采样离散摘要 `3e7cb1abde8dd2c2`；曲线48格×5000局摘要 `8dddb4014a4b491d`，Editor/最终包严格离散一致，派生浮点容差1e-12。概率、价格、假设和实际机器人数据见 BALANCE_CONFIG.md。

正常冷启动没有自动驱动参数：默认菜单就绪、默认槽Test=0、未开局、玩家默认存档字节未变。实际保存路径以日志 `[MetaSave]` 为准，Development包可能在包内 `AnomalyLab/Saved/SaveGames`。

最终差异审计PASS：106个变更文件，1067个原Content哈希未改，仅14个目标Content，无删除，uproject扩展不变；`Saved/V04/T32/delivery_audit.json`。v0.3只读清单1869文件PASS：`Saved/V04/T32/readonly_verify_20261013T131933.json`。

恢复演练：`Saved/V04/T32/RestoreValidation_20261013T132647`，1452文件逐一SHA复制校验，迁移后的完整独立包冷启动7项及资源/装备29项通过；恢复源码未另行编译。最终归档与验证索引 `Saved/V04/T32/release_archive.json`、`archive_verification.json`；最终阶段恢复点索引 `Saved/V04/checkpoint_T32_rc_verified.json`。索引仅在对应操作成功后生成。

## 画面与人工边界
已实际查看菜单/中文指南、商店、扫描、五格背包、观察者红眼、撤离与死亡代表帧；保留真实渲染截图和日志。完整最终包720p/1080p指南复查记录见T32_REPORT.md。自动输入与分支夹具不等于实体键鼠试玩，未完成听感验收。

最终包11张已查看帧的确切路径与截图时序限制见 `Saved/V04/T32/visual_review.json`，不按文件名推断实际画面内容。

用户已确认总体人工验收通过；观察者公平性、扫描信息价值、升级/诱饵/价格体验、3–5分钟节奏、声音与性能的逐项指标未提供。至少5位未参与开发者每人3局目标没有人数/局数记录支持，不宣称完成；PLAYTEST_RECORD.md保留未填的详细字段，用户总体确认记录见ACCEPTANCE_LOG.md。

## 恢复与限制
v0.3已验收归档独立保留，当前旧包和中间失败报告不删除。各阶段SHA恢复索引 T27_verified 至 T32_rc_verified 已通过。当前人工验收索引Saved/V04/accepted_release.json，原工程归档的HumanPending名称及SHA保持原样，本次验收文档单独保存。无Git，均为同盘恢复副本；归档不含个人SaveGames。恢复到新目录，勿覆盖后续工程；复制完整Windows可直接运行，源码重编需UE5.8及原插件/工具链与新ASCII构建上下文。坏主档恢复上一备份可能少一次最近提交；故障注入不等于真实断电实验。
