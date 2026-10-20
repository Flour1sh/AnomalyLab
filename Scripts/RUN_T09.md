# Windows Development 打包维护说明

本阶段复用现有 uasset，不生成或重建玩法资产。Python 调用本机 UE 5.8
AutomationTool 执行 build/cook/stage/package/archive，不使用 MCP、屏幕接管，
不启动游戏或 PIE。工程仍为 Blueprint；UE 因已有插件生成的临时构建目标属于
Intermediate 构建产物，不是新增 C++ 玩法。

注意：T09、T10 已获用户确认完成。此脚本仍是历史阶段构建器，预检硬编码了
`Current Ticket: T09` 和 `Last Completed Ticket: T08`，当前 STATE 下会主动失败。
后续重打包应先调整脚本预检以接受当前完成状态，并保留资产/配置检查；不要回改 STATE。
本次清理不修改 Python 脚本。完成上述维护后，在 `F:\AnomalyLab` 的 PowerShell 中执行：

```powershell
python '我的项目3/Scripts/build_t09.py'
python '我的项目3/Scripts/build_t09.py' --package
```

第一条仅检查文件和配置；第二条实际打包。引擎默认 `E:/UE_5.8`，可用
`--engine` 指定。需要本机 UE、Windows SDK 与对应构建工具；UE 构建缓存目录
须可写。脚本不会安装工具或改变插件启用状态。

配置：Win64 / Development，显式包含 `/Game/Prototype/Maps/L_Prototype`，
Pak + IoStore。每次输出使用独立 UTC 时间目录，避免覆盖之前打包结果：

- 包：`Builds/T09/<UTC时间>/Windows/`
- 报告及日志：`Saved/T09/<UTC时间>/build.json`、`packaging.log`、`UAT/`
- 最近报告：`Saved/T09/latest.json`

本机 MSVC 在中文工程路径创建 PCH 时出现 C1083，关闭 UBA 后仍失败。
脚本因此先将工程描述、Config、Content（以及存在时的 Plugins）复制到
`F:/AnomalyLab/T09BuildWork/<UTC时间>/AnomalyLabT09.uproject` 再构建。
这是独立文件副本，不是硬链接，不改变源工程名称或插件配置；输出 EXE 名称
为 `AnomalyLabT09.exe`。临时副本保留用于诊断，本脚本不自动删除旧输出。

`Config/DefaultGame.ini` 同时补充 GameFeatureData 的 PrimaryAssetTypesToScan
条目（AlwaysCook，无新增扫描目录），对应 UE GameFeaturesEditor 自带修复
逻辑。本机首次 Cook 缺少该条目报错并返回 ExitCode 25；这是打包阻塞修复，
没有新增 GameFeatureData 资产或改变现有插件启用状态。

打包 PASS 要求 UAT 成功退出、成功标记、EXE 和 IoStore 容器存在，且 19 个核心
源包的 SHA-256 保持一致。这不代表实际启动、输入或玩法测试通过；文件预检
也不能替代蓝图编译或引用完整性检查。

## 后续测试

保留整个 Windows 输出目录，不要只复制 EXE。用户准备好后启动包内顶层 EXE，
记录测试开始/结束时间，验证默认地图、移动、
观察、跳跃、E 开箱、HUD、奖励、怪物追逐、第二次 Threat 结束及 R 重开。
检查该 Development 包实际生成的 Saved/Logs；必要时启动时指定绝对日志路径。
编辑器 MCP/PIE 的结果不能代替独立 EXE 冒烟测试。新包通过后记录实际输出路径和测试结论。
现有 T09 包已获用户确认，不包含 T10；从当前源码新打包时还应检查蜥蜴朝向和身体动作。
