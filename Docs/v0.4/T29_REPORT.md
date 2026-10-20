# T29 跨局持久化与结算

## PLAN（T28 恢复点 20261012T085111 / 1310 文件校验 PASS 后开始）
- 扩展现有 ProgressionSubsystem 的受控 Commit，使用 USaveGame 内存序列化，外层长度/CRC 校验，保存至项目支持的 Saved/SaveGames。
- Schema 2；Schema 1 明确迁移/合法化，未来版本保留原档并禁止覆盖。无档默认 0；坏档从验证过的备份恢复，否则安全默认并保留坏档证据。
- 写临时文件、读回校验、保存旧有效主档备份，再替换主档并复核；中断时主档或备份至少有一个完整版本。持久化失败不更新内存 Meta、不假报购买成功；可检查磁盘后重试。
- 永久状态含余额、升级、预存诱饵、历史和有限最近结算/购买幂等键；不保存 HP/携带/扫描余量。购买与新局消耗均先提交存档再应用；只有物理入口延迟复核通过的成功终局增加收入。
- 添加不可变 EndRunSnapshot，只从封闭终局记录结算 UI；死亡/Error/菜单退出不新增收入。
- 自动化显式独立 Automation_* 槽；即使忘记传槽，已知测试开关也自动隔离。测试结束清理自身槽族，不覆盖玩家档。
- 验证：冷启动购买→进程关闭→重启恢复；缺档、坏档、备份、Schema 1/2/未来、非法值、保存失败/中断、重复结算/交易、死亡竞态，原有全流程/区域/Legacy。

## IMPLEMENT / VERIFY
- 新增 AnomalyMetaSaveGame.h/.cpp；扩展 ProgressionSubsystem、Coordinator 的终局快照与只读呈现；测试驱动/脚本增加隔离槽和异常清理。存档仅包含 Meta，不含局内物品/HP/扫描次数。
- 编译 PASS：build-editor_20261012T010225733938Z.log。新增持久化阶段未发生 C++ 编译失败。
- 10 个独立 UE 进程、26 项保存断言 PASS：Saved/V04/T29/Suite_20261012T090304375543/report.json。覆盖 CRC、缺档、Schema 1/2 合法化、未来版本实际冷启动保护、临时文件后中断、坏主档备份恢复、购买写失败/重试、强退无携带收入/不复制诱饵、两个 OS 进程购买恢复、物理入口保存失败转 Error。
- 持久化后的商店/真实输入/升级/五格/诱饵 29/29，1080p 实景：Saved/V04/T29/Runs/20261012T090430027312_editor。
- 一次 UI 测试误传空 -V04SaveCase=，UE 将后续参数读为用例名；失败报告保留于 20261012T090318157173_editor。脚本改为只传非空参数后重跑通过，未放宽断言。
- 原有菜单→整备→真实输入探索/撤离/死亡/重开 172/172 + 菜单 3/3：Saved/V03/Runs/20261012T085902978447_render_1280x720；新增永久余额保留、下一帧授权成功才付款、重复终局不可变断言。
- 实际查看 1080p 整备存档状态、720p 撤离成功/死亡永久余额快照，文字完整。
- 自动测试资金是专用槽运行时注入。所有正常默认 Meta 仍为 0；测试槽族在进程结束/异常时清理，原始 JSON/日志保留。没有读取 v0.3 Wallet 初始化 Meta。
- 当前保存采用“临时文件+读回+旧有效主档备份+替换后再校验”；备份回退到上一完整提交并明确提示，不宣称数据库或硬件断电测试。
- 区域 78/78，摘要仍 3e7cb1abde8dd2c2：Saved/V04/T26/Runs/20261012T090605350096_editor_logic_1280x720。Legacy flow 66/66：Saved/T18/editor_flow_20261012T090607.log。真人样本未收到；不将冷启动脚本成功当人工验收。

Status: Implemented / Automated Verified / Visual Verified；Human Accepted pending。

Rollback: Saved/V04/checkpoint_T29_verified.json（生成后有效）；退回 T28 使用 checkpoint_T28_verified.json，复制 Project 到新目录。项目快照不包含个人 SaveGames，恢复源码不覆盖存档。
