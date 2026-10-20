# T11E 构建与验收记录

T11 已由用户验收。T11E 于 2026-09-30 构建完成；本阶段只使用 C++、Blender/Python 和无界面 UE Python 命令行，不启动 UE MCP 扩展或屏幕接管。

## 实现

- `Source/AnomalyLab/Public/AnomalyEquipmentComponent.h` 与 `.cpp`：玩家开局持金属探测仪。`1` 在三仪器间循环，`2` 切到不可使用的枪，从枪按 `1` 回上次仪器。切换时调用 `CancelUse` 接口并下压手持模型 0.12 秒；枪只显示“武器功能尚未启用”，没有射击输入或伤害逻辑。Q 扫描在 T12 实现。
- `Source/AnomalyLab/Private/AnomalyBoxActor.cpp`：使用独立的 `VisualStream` 依据 DefinitionAsset 各自抽金属加固、警示标记、磨损。Safe 为 30/20/30%，Risky 为 70/60/50%，Unknown 及三个隐藏配置为 50/40/80%。附件无碰撞且附着于现有木箱，结果抽取仍使用独立的 `OutcomeStream`。
- `T11EAssets/generate_t11e.py`：生成 `.blend`、7 个 FBX、预览图及 `generation.json`。四个手持模型和三种附件由低面数几何构成，可重建。
- `Scripts/build_t11e_assets.py`：备份两个原有蓝图包后导入网格、材质，设置箱子和玩家组件引用。`Scripts/verify_t11e_assets.py` 在新进程独立重载核对引用。

## 重建顺序

在项目根目录 `F:/AnomalyLab/我的项目3` 执行：

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --python T11EAssets/generate_t11e.py
python Scripts/cpp_migration.py build-editor
python Scripts/cpp_migration.py editor --script build_t11e_assets.py --phase t11e-build
python Scripts/cpp_migration.py editor --script verify_t11e_assets.py --phase t11e-reload
```

`build-editor` 使用 ASCII 路径副本避开原项目中文路径的 MSVC 问题，成功后部署原生模块。`editor` 模式以 NullRHI/隐藏命令行启动，并在命令行禁用 MCP 插件。切勿重跑 T00–T11 旧蓝图生成器。

本次备份：`Saved/T11E/Backup_20260930T180306/` 中的 C++ 源文件；`Saved/T11E/BlueprintBackup_20260930T182258/` 中的两个蓝图。生成报告：`Saved/T11E/build_report.json`、`Saved/T11E/reload_report.json`、`Saved/T11E/bounds_report.json`。编译和 UE 命令行详细日志在 `Saved/CppMigration/20260929T083920372566Z/`。

## 人工验收清单与结果

2026-10-02，用户反馈“我认为没问题了，测试通过”，T11E 标记为人工验收通过，可进入 T12。下列清单保留为测试范围参考；用户未提交逐项操作记录，因此不把每一项单独标记为已验证，也不将这次反馈记为独立包验收。

1. 启动原项目地图 `L_Prototype`，确认右下方默认显示金属仪。连续按 `1` 核对金属→生物→物质→金属；按 `2` 换枪，点击鼠标不射击，再按 `1` 恢复之前的仪器。装备切换应有短暂下压反馈，移动/跳跃/观察/E 开箱/R 重开仍可用。
2. 重开数轮，确认箱子可见金属加固、警示标记、磨损的不同组合；同一类型可有不同组合，警示或加固不代表必然危险。查看开箱时附件不应阻断动画或玩家走位。
3. 检查箱型/隐藏配置/概率的 T11 临时浮字已消失。Q 此时不产生扫描读数，枪不造成伤害；这些是当前阶段范围。

自动证据确认 C++ 编译、FBX 导入、材质与蓝图引用在新 UE 进程中重载通过。无界面运行本身不能证明实体按键、画面位置、附件穿插、动画或导航表现；T11E 的实际测试结论由上述用户反馈提供。T12 扫描与 v0.2 独立包完整验收仍属后续阶段。
