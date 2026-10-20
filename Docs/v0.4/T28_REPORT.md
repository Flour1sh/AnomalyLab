# T28 局外整备与商店

## PLAN（T27 恢复点 20261012T083510 校验 1302 文件 PASS 后开始）
- 新增原生 Preparation 阶段（追加枚举值），仅探索地图显式启用；不生成箱子/威胁、暂停移动。E 入局，局内入口不提供购买权限。
- GameInstanceSubsystem 管理跨关卡内存 Meta；初始余额 0，不读取 v0.3 Wallet。T28 成功撤离记入内存 Meta；T29 再扩展持久提交。
- ProgressionConfig DataAsset 定义四商品价格/上限/效果。电池永久每级三种仪器各 +1（最多 2 级）；精度每级减少 25% 干扰/区间扩展、最多 2 级；背包 4→5；诱饵买入下局携带 1 个、F 落地、1200cm/5秒，冷却 3秒。
- 复用 ExplorationWidget 增加只读列表与永久余额，↑↓选、Enter 购买。Revision + 请求 Guid + 同帧限流保护，旧/重复/关店回调拒绝。
- 扩展 Inventory 动态容量，原 Capacity=4 保留为兼容默认；ThreatCharacter 复用导航，增加临时诱导目标。保持追逐/伤害参数。
- 改动：ProgressionConfig/Subsystem、Coordinator、Scanner、Box、Inventory、Threat、ExplorationWidget，单一资产生成脚本及专用边界测试；旧回归通过真实 E 进入准备阶段。
- 验证：编译、独立重载、余额不足/上限/重复/失效Revision/关店/快速购买；真实扫描精度、五格拾取、诱饵导航目标/到期回归；两档真实 UI 及 v0.3/Legacy。

## IMPLEMENT / VERIFY
- 新增 AnomalyProgressionConfig.h/.cpp、AnomalyProgressionSubsystem.h/.cpp；扩展计划所列原生组件、被动 HUD 和显式测试驱动。没有改名/删除既有 BP、定义、菜单或 Legacy 地图。
- 资产仅新增 DA_ProgressionConfig，修改 L_Prototype 与 WBP_ExplorationPrompt；生成前备份在 Saved/V04/T28/Assets_*，独立进程重载 22/22 PASS。
- 编译先发现 EngineUtils 缺失和 Box 局部变量重声明，暂停新增功能后修复；最终 build-editor_20261012T004804250009Z.log PASS。
- 两档真实渲染事务/效果测试各 29/29：Saved/V04/T28/Runs/20261012T084825254126_editor（720p）、20261012T084827426021_editor（1080p）。方向键选择、Enter 余额不足、F 使用均通过真实输入队列。测试资金为隔离进程的运行时注入，不是默认起始货币。
- 覆盖配置非法、不足余额、同帧连击、重复 Guid/过期 Revision、所有上限、入局关闭购买、开局只一次、5/5/5 升级、误差缩窄、五格/第六物品拒绝、诱饵实际导航靠近源、5 秒到期恢复玩家目标。
- 原有菜单/探索/追逐/拾取/死亡/重复结算/重开真实渲染路径 162/162 + 菜单 3/3：Saved/V03/Runs/20261012T084345376854_render_1280x720。
- T26 78/78，随机摘要保持 3e7cb1abde8dd2c2：Saved/V04/T26/Runs/20261012T084826364145_editor_logic_1280x720。
- 两档商店、失败原因、已购买状态、第五格截图已实际查看，中文完整；不据此声称真人手感或听感通过。
- Legacy 三套 52/47/66 PASS：Saved/T18/editor_stats_20261012T084922.log、editor_decision_20261012T084925.log、editor_flow_20261012T084937.log。存档留到 T29；T28 内存余额不会跨程序重启。观察者免疫说明已预留，具体行为在 T30 验证。

Status: Implemented / Automated Verified / Visual Verified；Human Accepted pending。
Rollback: Saved/V04/checkpoint_T28_verified.json（生成后有效），回到 T27 可使用 checkpoint_T27_verified.json；均复制 Project 到新目录并校验。
