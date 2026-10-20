# v0.2 P0 基线检查与恢复说明

完成日期：2026-09-25。结论：P0 PASS，可按计划进入 T11；本阶段未实现 v0.2 玩法。

## 检查结果

| 项目 | 实际结果 |
|---|---|
| 工具环境 | UE 5.8.0、Python 3.12.10、Blender 5.1.2、MSVC 14.44.35207、Windows SDK 10.0.26100.0、UE .NET 10.0.203 可用；SDK 10.0.22621.0 也已安装 |
| Blender | 后台 factory-startup 启动、读取 bpy 版本、正常退出；没有生成模型 |
| 工程配置 | 默认/编辑器地图均为 L_Prototype；Development 与 MapsToCook 配置存在 |
| 源码备份 | 1,059 文件，1,527,941,583 字节；复制时逐文件检查 SHA-256，检查后再次复核全部通过 |
| UE 资产检查 | 19 个核心包：18 个非地图资产加载、13 个蓝图严格编译、1 张地图加载；共 73 项检查通过 |
| 直接依赖 | 核心包的直接 hard/soft /Game 依赖未发现缺失；不声称扫描了全部工程递归依赖 |
| 地图 | 44 个 Actor，1 个 BoxSpawner 位于 (0,0,50)，没有预放置的游戏箱子，有 NavMeshBoundsVolume 与 RecastNavMesh |
| T10 基线比较 | 蜘蛛原玩法 60 个节点的类型/引脚/连线与历史基线一致；其余 18 个核心包哈希与 T10 基线一致 |
| 修改保护 | 检查前后 Content、Config、uproject 无修改、缺失或新增；未调用资产保存 |
| 未执行 | PIE、实际键鼠游玩、视觉验证、打包与独立 EXE；旧验收记录继续有效，但不是本次重测结果 |

## 当前实际蓝图基线

- BPC_Interaction：InteractionDistance=300；接口交互图未发现具体 BP_AnomalyBox 动态转换。
- BP_AnomalyBox：RevealDelay=1、bOpened=false、bResolved=false、bForceOutcome=false；HighValueAmount=5000、TrashAmount=3，ThreatClass 仍为 BP_Spider。
- BPC_Wallet：Money=0。
- BP_BoxSpawner：RoundState=Ready，MaxThreats=2、NextRoundDelay=3、SpawnRetryDelay=1、MaxSpawnRetries=3，当前 Actor 引用为空。
- BP_Spider：MoveSpeed=350、AcceptanceRadius=80、AutoResolveDelay=3、bAutoResolveThreat=true；T10 标记与 T10FacePlayer/T10AnimateBody 存在。
- 玩家 CharacterMovement.MaxWalkSpeed=350；IMC_Prototype 仍为 E 交互、R 重开。
- 本阶段没有将上述 v0.1 参数改成 v0.2 的 330 移速、20 秒威胁或新的奖励表。

## 备份与证据位置

基线目录：`F:/AnomalyLab/我的项目3/Saved/P0/20260925T115019971182Z/`

- `source/`：可恢复的源文件副本。
- `manifest.json`：逐文件相对路径、大小、SHA-256 与备份范围。
- `verification.json`：备份完整性及当前受保护源文件复核结果。
- `environment.json`：环境路径、版本、配置检查与磁盘信息。
- `unreal_inspection.json`：73 项检查、成员默认值、委托、图节点/引脚/连线、地图和直接依赖。
- `baseline_comparison.json`：与 T10 前玩法及其他核心包的比较。
- `unreal_inspection_20260925T195242.log`：成功运行的 UE 日志。
- `unreal_inspection.log`：首次因 Zen 缓存启动失败的日志，保留用于诊断。
- `completion.json`：阶段结果汇总。

`Saved/P0/latest.json` 指向本次基线。后续创建新快照时该指针会更新，上述时间目录不会被覆盖。

备份包含完整 Content（包括外部 Actor/Object 包和第三方素材）、Config、当时 Scripts/Docs、两个 Blender 源目录、uproject、根目录 Markdown，以及供历史比较使用的少量 Saved JSON。存在的 Plugins/Source 也由脚本纳入。
不备份构建输出、Binaries、Intermediate、缓存、绝大部分 Saved、.codex 或 Python 缓存。它是源工程恢复点，不是引擎安装或已有 EXE 的完整备份。

## 本次发现与处理

1. 默认 Zen 缓存启动失败，导致 UE 在执行检查脚本前退出，原因是没有可写缓存节点。
   `RUN_P0.ps1` 改为仅在检查进程使用引擎内置 `InstalledNoZenLocalFallback`，缓存写入 `Saved/P0/DerivedDataCache`。
   成功日志确认该路径可写；没有修改工程/引擎配置，也没有禁用系统服务。未来其他启动器若使用默认缓存仍可能需要相同处理。
2. 旧 `build_t09.py` 仍要求历史 T09/T08 状态，不适用于当前源码状态。留待 T18 维护，不回改 STATE。
3. 旧验证器含历史包哈希和节点名称断言，不能整套当作 v0.2 验证器。P0 新检查只读取/编译内存对象，不调用旧生成逻辑，也不覆盖历史验收报告。
4. 项目没有 Git 仓库；本阶段依靠完整源快照和哈希记录建立恢复点。

## 后续最小修改入口

| 阶段 | 入口与需要替换的旧行为 |
|---|---|
| T11 | BP_AnomalyBox EventGraph 的随机/金额读取；新增表和结构；保留 Wallet.AddMoney 与结果委托 |
| T11E/T12 | Character 输入路由、新装备/扫描组件及扫描接口、HUD；保留原移动/观察/跳跃 |
| T13 | Spawner 的 SpawnNextBox、HandleBoxInteractionStarted、CleanupCurrentRound；加入候选集合和选箱许可 |
| T14 | CompleteCurrentOutcome、EndRun、Character.T06RunEnded/T06Restart；替换自动下一轮与两次威胁自动结束 |
| T15 | Spider.EventGraph/ResolveThreat 及玩家 Health；替换一次攻击提示和 3 秒自动结算，保留 T10 动作 |
| T16–T18 | 替换 ThreatFallbackElapsed 的假成功兜底，完善状态/错误/UI/验证/打包 |

已确认的新契约见 `prototype_v0.2_decisions.md`。`01_CONTRACTS.md` 在对应功能真正实施后再逐项迁移。

## 重跑检查

在 `F:/AnomalyLab` 的 PowerShell 执行（UE 编辑器须已关闭）：

```powershell
# 可选：建立新的独立源快照，会更新 latest 指针。
python '我的项目3/Scripts/prepare_v02_p0.py'
# 加载/内存编译检查，不保存资产，不运行 PIE。
& '我的项目3/Scripts/RUN_P0.ps1'
# 校验指定基线的备份与当前 Content/Config/uproject。
python '我的项目3/Scripts/prepare_v02_p0.py' --verify 'F:/AnomalyLab/我的项目3/Saved/P0/20260925T115019971182Z'
```

检查脚本断言的是 v0.1+T10 基线。T11 开始改变行为后，不应通过修改游戏去迎合这些旧值；应建立相应阶段的新验收，并保留本次原始证据。

## 恢复方式

先关闭 UE 并保存当前工作到另一份快照。用 manifest 校验 source 副本后，将 `source/` 内容复制到新的空目录，以其中原名 uproject 打开，验证需要的资产；缓存由 UE 重建。此方式不覆盖当前工作。
若要原地回滚，先比较 manifest 和当前新增/修改文件，仅恢复明确需要的文件；不要删除未列在基线中的用户新文件。恢复后重跑检查及必要 PIE 回归。
本次已验证所有副本哈希，没有执行破坏性的原地回滚，也没有另建完整恢复工程运行游戏。
