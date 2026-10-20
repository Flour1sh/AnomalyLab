# T13 多箱回合构建

2026-10-02 按用户要求仅用 Python/C++ 构建，等待后续 UE MCP 测试。本次未启动 UE MCP 扩展、屏幕接管、PIE、玩法测试或打包。

## 实现

- `AAnomalyRoundCoordinator` 自带左、中、右三个可编辑 SceneComponent 生成点，默认相对 Y 为 -220/0/+220 cm。每轮三次独立抽 Safe/Risky/Unknown；若全部同型，随机替换一个槽为另一型。生成使用 deferred spawn，在 BeginPlay 初始化前写入箱型和轮次 ID。只有三箱全部有效时才登记候选并开放交互/扫描；残缺集合立即销毁，最多重试三次，每次间隔一秒，耗尽进入原型异常。
- `CandidateBoxes` 为当前轮完整集合，`SelectedBox` 为权威选择；`CurrentBox` 保留为旧诊断代码别名，选箱后指向所选箱。箱子通过 Coordinator 锁定成功后才置 `bOpened`。未选箱关闭 Visibility 射线交互，并用屏幕朝向的 UMG 组件显示“已锁定”；结算与回合结束统一移除委托、计时器、全部候选和结果 Actor。
- 扫描入口按完整候选集合、轮次 ID 和 Ready 状态判定。结果回调仅接受本轮所选箱；箱内原有 `bResolved` 防重复继续保证最多一次结果和付款。
- Python 脚本备份并重新编译/保存现有 `BP_BoxSpawner` 与 `BP_AnomalyBox`，生成 `/Game/UI/WBP_BoxLocked` 并赋给箱子蓝图。没有改动地图或第三方素材。

## 构建与证据

```powershell
python '我的项目3/Scripts/cpp_migration.py' build-editor
python '我的项目3/Scripts/cpp_migration.py' editor --script build_t13_assets.py --phase t13-build
python '我的项目3/Scripts/cpp_migration.py' editor --script verify_t13_assets.py --phase t13-reload
```

最终 Editor 编译退出码 0，UBT `Result: Succeeded`；资产构建和独立进程重载均退出码 0。报告在 `Saved/T13/build_report.json`、`Saved/T13/reload_report.json`。原有 uasset 备份路径由构建报告记录，原始进程日志保存在 `Saved/CppMigration/20260929T083920372566Z/`。初次沙箱编译因 UnrealBuildTool 用户缓存权限失败，重试编译成功；失败记录保留。

独立重载确认三个生成组件相对位置不同，三个蓝图编译通过、Spawner 仍引用箱子蓝图且箱子引用锁定面板。此结果只验证结构及可加载性，不证明场景间距、锁定文字字形、交互、扫描、随机组合、付款或故障恢复的实际玩法行为。

## 后续 UE MCP/人工测试

1. 实景看三箱并排是否可绕行、开启动画和视觉附件是否正常；检查“已锁定”中文字形与可读性。
2. 多轮记录候选数量与箱型组合，确认每轮至少两型；三箱分别可以对准和扫描，重新对准仍恢复各自缓存。
3. 连续按 E 或快速切换目标，仅一个箱开、一个结果、一次付款；未选箱不能继续交互或扫描。下一轮三箱重新生成且旧箱全部消失。
4. 分别覆盖奖励、垃圾、威胁、第二次威胁结束及 R 重开；检查旧回调不能推进下一轮。
5. 注入候选箱生成失败，核对残缺集合不可交互、有限重试以及耗尽后的异常终局。

## 人工验收（2026-10-04）

用户反馈：“测试通过了，写入日志”。据此将 T13 标记为人工测试验收通过，下一阶段为 T14 决策与终局。上述清单保留为范围参考；用户未提供逐项操作记录，不把总体确认展开成逐项测试结论。独立验收日志见 `Saved/T13/acceptance_log.md`。
