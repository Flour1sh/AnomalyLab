# Initialization + T26 stage report

用户于 2026-10-12 明确“验收成功”，T26 状态更新为 Human Accepted（总体确认）。没有收到逐项反馈、参与人数或局数，因此不补造这些记录。后续授权已扩展到依次实现 T27–T32；下文保留当时交付事实。

2026-10-12 / Asia/Shanghai。Baseline RC_20261011T225958。范围仅初始化 + T26；本文件不是完整 v0.4 FINAL_REPORT。

Status: Implemented / Automated Verified / Visual Verified. Human Accepted: pending (0 participants). 本轮停止于 T26。

## 改动与契约

区域现在是可编辑的 PrimaryDataAsset，并在 deferred spawn 前明确赋给候选箱；Box 保持原开奖职责。公开类型选择仍有“一轮至少两型”的修复，Unknown 的一次隐藏配置继续存在。复制区域/箱定义后应用乘数并校验归一化，扫描只读副本并按原接口缓存，结果仅揭晓时生成。

三份区域数据分别配置公开型权重、隐藏型权重、High/Trash/Threat 乘数、金额乘数、扫描误差增量与允许异常。当前允许集仅 Chaser，未实现类型拒绝。运行默认固定种子关闭；测试启用独立区域和箱流。Legacy 不进入新采样路径，不额外消费其随机数。

区域提示在原 HUD 中增量增加 RegionText/RegionBacking，靠近箱子时显示其区域名称/倾向，其余时显示三房概览。不展示隐藏 ID/精确概率，不接管输入。计数日志覆盖 open/scan/reward/threat/survive；面值与 Wallet、实得收入分开。

所有四格背包、扫描 1 秒/300 cm/遮挡/取消、选一锁二、跨轮携带、两次收容返程、入口手动 E、同帧死亡优先与 R 重开路径均保留。未加入 T27–T32 功能。

## 已执行验证

| 阶段 | 结果 | 证据 |
|---|---|---|
| v0.3 基线源/资产 | 初始化 1,124 Source/Config/Content 文件与验收清单一致 | 初始化 checkpoint manifest 与 release_manifest |
| v0.3 核心基线 | 146/146，默认菜单到完整探索/终局/重开 | Saved/V03/Runs/20261012T074637735362_logic_1280x720 |
| Legacy 基线 | stats 52/52、decision 47/47、flow 66/66 | Saved/T18/*20261012T0750*、*0751* |
| 真实 uasset 审计 | 六配置/地图/默认值 PASS | Saved/V04/initialization/asset_audit.json |
| Editor C++ 编译 | 两次 PASS，最终含完整固定种子测试驱动 | Saved/CppMigration/20260929T083920372566Z/build-editor_20261011T235706916154Z.log |
| T26 资产独立重载 | 43/43 PASS，非目标 Content 1,070 文件未变 | Saved/V04/T26/assets.json、reload.json |
| 原生统计/边界/cache | 78/78 PASS，180,000 区域开箱样本，另 18×10,000 结果频率采样 | Saved/V04/T26/Runs/20261012T075934391088_editor_logic_1280x720/report.json |
| Editor 720p / 1080p 区域实景 | 各 81/81、各 3 张；六张已查看中文无截断，固定种子完整统计一致 | Runs/20261012T080027906979_editor_render_1280x720、20261012T080116418599_editor_render_1920x1080 |
| 修改后 Editor v0.3 核心 | 146/146 PASS | Saved/V03/Runs/20261012T080023516322_logic_1280x720 |
| Win64 T26 检查点 | 最终构建 PASS，三房两档各 81/81；全序列摘要与 Editor 一致 | Builds/v0.4/AnomalyLab_T26_20261012T081026/Windows；Saved/V04/T26/package_report.json |
| Legacy 最终 Editor/包 | 两端各 stats 52/52、decision 47/47、flow 66/66 PASS | Saved/T18；阶段独立副本将保留至 Saved/V04/T26/Regression |
| 最终包 720p 核心实景 | 151/151、菜单启动另 3/3 PASS | Saved/V03/Runs/20261012T081248216942_render_1280x720 |
| 最终包 1080p 静音核心实景 | 151/151、菜单启动另 3/3 PASS | Saved/V03/Runs/20261012T081514366706_render_1920x1080 |
| 只读交付审计 | 9/9 PASS；v0.3 清单 1,869 文件未变、当前包源 1,130 文件一致、包文件 48 份 SHA-256 | Saved/V04/T26/delivery_audit.json、package_sha256.json |

实测统计与配置前后表见 BALANCE_CONFIG.md。上述统计不模拟死亡/撤离；机器人/合成输入不是人工试玩人数。

首包内部检查通过但严格 JSON 对照失败（五项约 1 ULP 浮点末位差异），原包/失败报告保留。测试增强为所有 180,000 采样的 seed/type/hidden/outcome/integer reward 全序列摘要严格一致，离散统计/缓存同样严格相等；仅派生浮点值和归一化概率采用 1e-12 相对/绝对容限。最终 Editor/包摘要均 `3e7cb1abde8dd2c2`。最终包对照证据分别为 `Runs/20261012T081202540279_package_render_1280x720`、`Runs/20261012T081212966244_package_render_1920x1080` 的 comparison.json；无生产概率/玩法修正。

## 文件范围与恢复

新增 RegionDefinition.h/.cpp、RegionSmoke.cpp；扩展 Box.h/.cpp、Coordinator.h/.cpp、ExplorationWidget.h/.cpp、AnomalyLab.cpp；新增区域资产三个，原资产仅探索地图/HUD 两个。Scripts 新增审计/构建/重载/统计执行/打包/配置表/快照工具，Docs 同步当前接口/资产/阶段进度。

初始化恢复点 `Saved/V04/Checkpoint_20261012T074812_initialization/`，1,279 文件校验 PASS；资产前备份 `Saved/V04/T26/AssetsBefore_20261012T075902087073/`。恢复到新目录，避免旧恢复点叠加保留新增文件。验收 v0.3 归档不作为工作目录；初始化误调用旧 verify 更新了其派生 verification_report.json 的时间，所有清单文件一致；后续只读审计结果写 Saved/V04。

T26 最终恢复索引 `Saved/V04/checkpoint_T26_verified.json` 仅在 checkpoint_v04.py 完成逐文件 SHA-256 校验后写入，指向带 manifest.json/README_RESTORE.md 的完整 Project 快照（包含 Editor binaries）。本阶段完整 Win64 目录独立保留于 `Builds/v0.4/AnomalyLab_T26_20261012T081026/Windows/`；包哈希清单 `Saved/V04/T26/package_sha256.json`。阶段证据副本 `Saved/V04/T26/Regression/`、汇总 `regression_summary.json` 已核对最终 EXE 命令、每张核心截图尺寸和逐区域日志。

精确修改/新增文件列表见 `Saved/V04/T26/delivery_audit.json`（审计后仅补充文档和 finalize_t26_evidence.py）；无任何 Config 或其他 Content 改动。Python 脚本语法检查通过。完整实际测试命令/日志入口集中于 `Scripts/RUN_V04_T26.md`，失败原因和恢复方法均记录。

## 未完成的人工项

当前真人样本 0。真实键鼠、听感、三房提示是否易理解、风险收益取舍是否有趣仍待用户验证。操作清单 ACCEPTANCE_CHECKLIST.md；复跑命令 Scripts/RUN_V04_T26.md。工程门槛通过后本轮止于 T26，不启动 T27。
