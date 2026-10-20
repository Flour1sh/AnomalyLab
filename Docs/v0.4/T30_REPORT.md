# T30 观察者异常

## PLAN（T29 恢复点 20261012T090824 / 1316 文件 PASS 后开始）
- 原生 AAnomalyObserverCharacter 继承已有 ThreatCharacter，复用导航、伤害冷却、20秒收容、终局清理；独立 Warning / Observed / Unobserved / Unobservable / Resolved 状态。
- 以实际相机到眼部的距离 + 点积视锥 + Visibility Trace 判定；进入/退出阈值不同、0.18秒失视宽限、0.2秒最短驻留和0.08秒获取时间防抖。
- 正视停步，背对/遮挡接近；接触前0.35秒容错。累计抑制4秒后红眼1.25秒暂不可抑制，HUD 明示；20秒独立收容，保持玩家/怪物速度与既有伤害。
- DataAsset 配置全部阈值及材料；可重建低模几何，区别于蜘蛛。青色预警/正视提示、红眼提示；不受诱饵影响，扫描只给威胁等级、不预知最终怪物。
- 仅探索区域允许池显式扩展 Chaser/Observer；独立异常类型随机流，不消费开奖 RNG。默认观察者在混合允许池占35%；Legacy 保持 Chaser。
- 修改 RegionDefinition 支持已实现集合；Box/Coordinator 延迟生成和重试均使用已确定的异常类与配置。原 v0.3 回归显式验证原追逐者，另新增观察者完整路径。
- 验证：正视/背向/临界/墙体/快速旋转/超距/过载/导航失效/重叠/独立到期/伤害冷却/终局竞态，真实相机画面与原追逐者回归；真人可读性与逃生公平性单列待验收，不虚报。

## IMPLEMENT
- Source/AnomalyLab 新增 ObserverConfig.h/.cpp、ObserverCharacter.h/.cpp、ObserverSmoke.cpp；扩展 RegionDefinition、BoxActor、RoundCoordinator、ThreatCharacter、AnomalyLab、ProgressionSubsystem 与 V03Smoke。
- 新配置、三材料与三份区域允许池；修改探索地图和现有 WBP_HealthThreat 的 ThreatText 尺寸。Scripts/build_t30_assets.py 可重建，verify_t30_assets.py 独立重载，run_t30.py 隔离存档运行。
- 首次警告阶段无伤害；实际相机对眼部判定。观察者继承同一接触范围/25伤害/1.5秒冷却/330速度/20秒独立收容。类型抽取仅消费独立随机流，开奖序列不变。终局与死亡由原 Coordinator 清理 actor/timer。

## VERIFY / 失败与修复
- 最终 Editor 编译 PASS：build-editor_20261012T013215148586Z.log。早期 Mesh 局部名与 ACharacter::Mesh 遮蔽导致编译失败，改名后通过，未跳过测试。
- 原生逻辑 32/32：Saved/V04/T30/Runs/20261012T092926467288_editor/report.json。
- 最终 1080p 渲染 32/32：Runs/20261012T093237457057_editor；已查看红眼实际画面，眼部红色带与中文反制/倒计时清楚可见。720p 最终复跑结果随后追加。
- 首次渲染显示眼部局部藏于头部中，前移并增大后重新编译、渲染；导航丢失测试发现重复日志，增加无控制器保护。首次资产检查错写 HealthText，实际原控件为 HPText；按真实接口修正，未修改资产来迁就测试。
- 独立 UE 重载 PASS：Saved/V04/T30/reload_report.json。区域 78/78：Saved/V04/T26/Runs/20261012T093239020011_editor_logic_1280x720；全180000采样摘要仍 3e7cb1abde8dd2c2。
- 验证覆盖 E 自然开箱（固定种子搜索非强制结果）、预警、正视、背向、实际移动、迟滞阈值、墙体、超距、快速转镜、红眼及恢复、接触/冷却、无控制器、20秒独立收容、撤离死亡竞态、R 新局和活动期间死亡清理。

## REPORT / CHECKPOINT
- Human: 0。用户已明确选择“暂无真人样本，先交付待人工验收的 RC”。自动输入与位置夹具不算真人试玩；视觉可读性的人类确认、真实逃生手感和听感仍待验收。
- 回退：Saved/V04/checkpoint_T29_verified.json；本阶段全部工程检查通过后写 checkpoint_T30_verified.json。恢复到新目录，不叠加覆盖。
- 下一阶段 T31：测量后增加有界回合曲线和策略仿真，不改伤害/速度/两次收容上限。
Status: Implemented / Automated Verified（最终回归追加中）/ Visual Verified（已查看代表画面）/ Human Pending。


最终回归：720p Runs/20261012T093356507292_editor 32/32；1080p Runs/20261012T093237457057_editor 32/32；重载24/24；原追逐者完整流程 Saved/V03/Runs/20261012T093237416004_render_1280x720 172/172 + 菜单3/3；Legacy flow66/66（editor_flow_20261012T093357.log）。最终两档红眼已查看，工程阶段检查通过。Human Pending 按用户选择保留。
