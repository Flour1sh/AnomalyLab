# T27 扫描资源

## PLAN（2026-10-12）
- 复用 ScannerComponent 输入/计时、BoxActor 有效性及缓存；每种默认 3 次，可配置 0–20。
- Box 完成读数构造后，原生游戏线程扣费并写缓存；失败不写缓存、不扣费；缓存优先于资源检查。
- 取消继续复用既有真实输入路径。新局初始化资源；继续轮次不调用初始化；Legacy 不消耗。
- 改动 ScannerComponent、BoxActor、模块注册，新增明确开关的 V04 边界驱动和运行脚本。
- 验证：编译，0/1/满/缓存/重复/锁定/旧轮/独立预算/新局升级边界，v0.3 原有真实输入扫描取消与全流程，区域概率不变。
- HUD 将“扫描剩余”与“可靠性”分开；720p/1080p真实渲染检查。

## 实现与验证
依赖 T26 用户已于 2026-10-12 总体验收；不推断逐项人测数据。

- 编译首次链接失败（新增 cpp 未进入 UBT 文件缓存），构建脚本显式 NoUBTMakefiles 后恢复。补充测试曾发生 case 60 编号冲突，改为独立 590；未绕过测试，最终编译 PASS：build-editor_20261012T002931180642Z.log。
- 原生资源边界 10/10：Saved/V04/T27/Runs/20261012T082805446383_editor/report.json。
- T26 区域与缓存回归 78/78：Saved/V04/T26/Runs/20261012T082951371003_editor_logic_1280x720/report.json，逻辑摘要仍 3e7cb1abde8dd2c2。
- 720p 菜单至终局真实渲染自动路径 155/155，菜单 3/3：Saved/V03/Runs/20261012T082948232251_render_1280x720。新增真实 Q 超距、遮挡取消；原有松开与换装备取消追加“不扣费”断言。
- Legacy 流程 66/66：Saved/T18/editor_flow_20261012T083115.log。
- 1080p 全流程 155/155，菜单 3/3：Saved/V03/Runs/20261012T083049394983_render_1920x1080。两档扫描结果截图已实际查看，三行提示完整。
- 修改资产只有 WBP_ScanPanel（先备份，保持原树，仅扩大提示尺寸并自动换行）；独立 UE 游戏进程重新加载、渲染正常。
- 人工体验待测；T27 没有收到用户体验结论。独立包资源规则在 T32 最终包再次回归。

Status: Implemented / Automated Verified / Visual Verified；Human Accepted pending。
恢复：Saved/V04/checkpoint_T27_verified.json 指向完整快照，复制 Project 到新目录后校验/重建；不覆盖 T26 包。下一依赖：T28。
