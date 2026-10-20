# T11 Python 资产构建

> 历史记录：本文件描述 2026-09-27 的迁移前流程。2026-09-29 后 BP_AnomalyBox 及定义类已继承 C++。不要在现工程重跑下面的 RUN_T11.ps1 或 build_t11.py；会覆盖原生适配。当前构建/验证入口见 `../Docs/CPP_MIGRATION.md`。

授权范围（2026-09-27）：只构建 T11 所需 uasset。使用隐藏 NullRHI UE Python 进程，进程级禁用 MCP 插件，不改插件配置，不接管屏幕，不运行 PIE 或打包。

## 内容与构建入口

- 新建 BP_AnomalyBoxDefinition 与六个 DataAsset：Safe / Risky / Unknown 和三套未知箱隐藏配置。
- 修改 BP_AnomalyBox：生成时缓存配置，开箱时按权重抽结果，HighValue 按闭区间整数抽金额，Trash 仍为 3，Threat 不付款。
- 保留 bForceOutcome / ForcedOutcome、原有动画/音效/结果生成/Wallet 调用和防重复链。
- 不包含 T11E 装备、附件、T12 扫描、T13 三箱、HP 或回合决策。

关闭其他 UE 编辑器后，在 PowerShell 执行：

```powershell
& 'F:/AnomalyLab/我的项目3/Scripts/RUN_T11.ps1' -Mode build
# 首次创建定义类 schema，第二次创建定义实例与箱子 schema，第三次构建图。
& 'F:/AnomalyLab/我的项目3/Scripts/RUN_T11.ps1' -Mode build
& 'F:/AnomalyLab/我的项目3/Scripts/RUN_T11.ps1' -Mode build
& 'F:/AnomalyLab/我的项目3/Scripts/RUN_T11.ps1' -Mode reload
```

完成标记存在时不覆盖已构建图。失败的图构建不保存箱子图，重新执行从已保存 schema 继续。
修改前备份、源资产哈希、原始日志与构建报告位于 Saved/T11；baseline.json 指向箱子备份。
完整旧源码另有 Saved/P0/20260925T115019971182Z/source。

实现方式调整：已确认设计原先以 Struct + DataTable 为工程默认值；本机 UE 5.8 公开 Python
API 无法编辑 UserDefinedStruct 的字段，尝试未保存任何 Struct/DataTable。为遵守纯 Python
构建约束，采用原总体计划允许的 DataAsset 方案，不新增 C++ 或修改 MCP 扩展。
每个定义拥有相同 15 个命名字段，箱子初始化时复制到 Data* 实例变量，不修改共享资产。
DefinitionID=None 时等权选择 Safe/Risky/Unknown；可指定定义 ID，Unknown 再等权抽隐藏配置。
ResolvedDefinitionID 只供内部调试。bDefinitionInitialized 防止重复初始化；bDefinitionValid 拒绝非法配置。
ConfigurationStream 和 OutcomeStream 独立，bUseFixedSeeds 默认关闭，可供后续确定性测试。
外观概率和扫描误差仅存数据，实际附件与扫描留到 T11E/T12。
非法配置暂时拒绝该箱开箱并记日志；专用技术异常终局和 R 错误恢复由后续 T16 接入。

## 后续测试门槛（本轮不执行）

1. 每种箱型的实例配置生成后不变；Unknown 等权选择三个隐藏配置，不重复初始化。
2. 强制 HighValue / Trash / Threat 仍走原结果与 Wallet 路径；高价值付款落在实例范围内。
3. 重复 E 不重复开箱、付款或推进；奖励模型失败仍付款；威胁追逐、T10 动作、旧三秒结算不回归。
4. 按固定种子对每个实际分布各抽样至少 10,000 次，记录频率、偏差及边界 0% / 100%。
5. 参数非法或定义缺失时记录错误并拒绝开箱，不使用未初始化数据；正常终局验证 R 重开。
6. 实体输入/视觉/PIE 验收在用户开启 UE MCP 后进行。编译、重载成功不代表玩法验收通过。
