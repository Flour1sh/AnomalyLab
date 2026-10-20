# C++ 迁移记录

授权：2026-09-29，用户要求直接执行迁移并持续留日志。
范围：将现有 v0.1 + T10 + T11 核心玩法迁入 C++，保留 Blueprint 外观、交互入口、事件适配和 UI。v0.2 的装备、扫描、三箱、HP、20 秒威胁与撤离仍按后续阶段实施。

## 当前架构

| C++ 类 | 保留的 Blueprint | 职责 |
|---|---|---|
| UAnomalyBoxDefinition | BP_AnomalyBoxDefinition、六个 DA_Box_* | 原生数据字段、定义校验、加权结果选择 |
| UAnomalyWalletComponent | BPC_Wallet | 唯一金额状态、付款与溢出保护；旧函数和金额事件适配 |
| AAnomalyBoxActor | BP_AnomalyBox | 实例配置缓存、独立随机流、开箱计时、生成结果与付款；蓝图保留组件及 BPI 入口 |
| AAnomalyThreatCharacter | BP_Spider | 追逐、一次攻击提示、威胁计时与清理；蓝图保留 T10 外观动画 |
| AAnomalyRoundCoordinator | BP_BoxSpawner | 选择锁定、状态、结果清理、重试、威胁计数和终局；旧枚举/事件适配 |

`Source/AnomalyLab/` 是 Runtime 模块；Game 和 Editor Target 均使用 UE 5.8 BuildSettings V7。`.uproject` 仅新增模块声明。
玩家、交互组件、HUD、地图、输入配置与第三方模型资产未修改。旧 Blueprint 事件保留给现有 HUD/玩家，C++ 原生委托连接箱子、轮次和威胁；不会同时执行两套旧玩法图。

本次保留现有单箱、怪物速度 350、3 秒威胁结算、第二次 Threat 自动结束、R 重载的行为。未来 v0.2 变更以 `prototype_v0.2_decisions.md` 为准。可编辑配置及 Blueprint 展示事件为后续系统提供接入点；尚未实现枪械、伤害或商店。

## 备份、日志与恢复

- 迁移前完整备份：`Saved/P0/20260929T080155538340Z/source/`，1,074 文件、1,528,582,905 字节。
- 本次日志目录：`Saved/CppMigration/20260929T083920372566Z/`；入口 `Saved/CppMigration/latest.json`。
- `journal.jsonl` 逐条记录时间、命令、PID、返回码、资产阶段和失败原因；原始 stdout/UE/UBT 日志保留。
- `pre_migration_assets.json` 保存迁移前变量、默认值、组件、图节点和连接；`baseline_manifest.json` 保存文件哈希。
- ASCII 构建副本：`F:/AnomalyLab/CppBuildWork/20260929T083920372566Z/`。源工程仍使用原目录和原 `.uproject` 名称，构建副本避开中文路径的编译兼容问题。

恢复时关闭 Unreal 进程，先保留当前工程，再把完整备份复制到另一个目录打开。备份无 C++ 模块；不要把迁移后 `.uproject`、Source 或原生 DLL 混入恢复副本。无需删除或覆盖当前工程即可检查旧版本。

## 验证与维护入口

关闭使用当前模块的 Unreal 编辑器后执行：

```powershell
Set-Location 'F:/AnomalyLab'
python '我的项目3/Scripts/cpp_migration.py' build-editor
python '我的项目3/Scripts/cpp_migration.py' editor --script validate_cpp_migration.py
python '我的项目3/Scripts/cpp_migration.py' package
python '我的项目3/Scripts/cpp_migration.py' smoke
```

构建工具会写本机 Unreal/MSVC 缓存；编辑器验证使用隐藏 NullRHI 和进程级文件 DDC 回退。正常游戏启动不使用 `-AnomalyMigrationSmoke`；该标志仅启用自动回归驱动，Shipping 不自动创建驱动。
源码修改后先编译 Editor 再打开工程。不要依靠 Live Coding 完成反射字段或父类修改。
原工程目录名包含中文，直接在原路径触发 MSVC 全量编译时，PCH 路径会出现乱码；本脚本在 ASCII 工作副本编译，并把 DLL、`UnrealEditor.modules` 与 `AnomalyLabEditor.target` 收据部署回源工程。不要只复制 DLL。`DefaultEngine.ini` 中的 `DefaultEditorTarget=AnomalyLabEditor` 和 `DefaultGameTarget=AnomalyLab` 让双击原始 `.uproject` 时明确选择目标。2026-09-30 用户打开工程时曾因缺少该设置而遇到“Found multiple targets”构建失败；补齐设置和收据后，用原始路径启动编辑器，日志确认原生模块加载、引擎初始化并打开 `L_Prototype`。诊断日志：`Saved/CppMigration/20260929T083920372566Z/direct_project_open_unsandboxed.log`。

`migrate_cpp_assets.py` 是此次迁移工具，按 export / definition / gameplay 阶段执行并保存版本标记，不能作为日常资产生成器。不要重跑旧 T04–T11 图构建脚本覆盖原生继承与适配图。旧 `build_t09.py` 不复制 Source，不适用于当前工程打包；改用上述入口。

已完成：Editor 与 Game C++ 编译、资产分阶段编译保存；新进程重载检查通过，14 个 Blueprint 编译、六套定义值、原生父类、T10 图、依赖和地图实例均通过。哈希确认只修改预定 11 个 Content 资产，无新增 Content/Config，无无关修改。

最终 Win64 Development 包：`Builds/CppMigration/20260929T083920372566Z/Windows/AnomalyLab.exe`。最终 UAT 日志 `Saved/CppMigration/20260929T083920372566Z/package_20260929T180713631009Z.log` 为 `BUILD SUCCESSFUL`、ExitCode 0。编辑器实景自动回归 `editor_runtime.json`：97/97 检查通过；最终独立打包程序回归 `packaged_runtime.json`：97/97 检查通过，包含六套配置的 60,000 次固定种子抽样、动画运行时实例、地图导航、接触通知、付款和防重复、两次威胁及重载。`final_audit.json` 10/10 检查通过，覆盖完整备份 1,074 文件哈希、最终 Source 与打包工作副本一致、资产改动范围和运行报告。

迁移日志保留了一个已更正的测试误报：最初检查动画组件的编辑器 `AnimationData` 而非运行时 `UAnimSingleNodeInstance`，因此报 FAIL；运行时实例检查证实木箱动画实际正常播放。也保留了路径/构建目标/本机 API 探索时的失败日志，不能将历史所有尝试描述为全程零错误。最终包的自动结果为 PASS。

NullRHI 自动运行不能替代实体 E/R 按键、画面和音效的人工验收；自动驱动直接调用玩法接口并通过关卡重载路径检验重置。启动中原有 GameFeatureData 类加载 ensure 不归为新增迁移错误。

## 2026-09-30 高价值提示修复

用户试玩发现钱包累计金额正确，但 `WBP_PrototypeHUD.ShowOutcome` 仍显示迁移前写死的 `HIGH VALUE +$5,000`。已修改 HUD 和角色蓝图：角色从当前箱子 `HighValueAmount` 读取本次实际奖励，作为 `RewardAmount` 传给 `ShowOutcome`；HUD 用数字分组格式化并显示 `HIGH VALUE +$实际金额`。垃圾与威胁文案未改。修改前两项 uasset 的逐文件备份、构建报告和独立重载报告位于 `Saved/CppMigration/HudRewardFix/20260929T183952383512Z/`。

最终打包日志 `Saved/CppMigration/20260929T083920372566Z/package_20260929T184308582772Z.log` 为 `BUILD SUCCESSFUL`。独立程序回归 `packaged_runtime.json` 现为 98/98；其中一次实际高价值奖励 $3,510，结果提示也为 `HIGH VALUE +$3,510`。修复前文中的 97/97 与旧包日志仅描述当时状态，当前交付以本节和最新 `final_audit.json` 为准。重新打开编辑器后再观察蓝图/PIE，避免旧进程持有过时资源。
