# T19 — 游戏初始菜单与 Level01

日期：2026-10-10。

状态：实现、编译、资产重载、实际渲染和独立包验证完成；菜单人工体验验收 `PENDING_MANUAL`。

## 用户范围与产品行为

用户确认原 T19 基线人工审计完成，并将当前 T19 改为具有成品游戏感的初始界面。参考 How to Fish / 致命公司，采用实验室实景、复古工业终端、暖橙选中状态和简洁纵向菜单，保留独立 AnomalyLab 标识。没有复制参考游戏的素材。

启动 → `L_MainMenu` → “开始游戏” → 加载卡 → 现有 `L_Prototype`（玩家可见 Level01）。

菜单项：

- 开始游戏：单次切图请求；加载期间拒绝重复开始；目标包缺失时显示错误并保留菜单。
- 设置：1280×720 / 1920×1080、窗口 / 无边框全屏、低 / 中 / 高 / 极高画面质量；先编辑草稿，应用后经 `UGameUserSettings` 生效并保存，返回放弃未应用草稿。
- 操作指南：只描述当前已实现的 v0.2 控制与三箱规则，不提前宣称已实现拾取或新撤离系统。
- 退出游戏：确认页默认选中取消；确认后退出桌面。

支持鼠标悬停/点击，↑↓ 或 W/S 选择，Tab/Shift+Tab 循环，Enter/Space 确认，Esc 返回；主菜单 Esc 打开退出确认。短促按钮音及低强度底噪均由本地脚本确定性生成，不依赖网络资源。

## 实现落点

- `Source/AnomalyLab/Public/AnomalyMenuGameMode.h` 与对应 cpp：菜单专用 GameMode/Controller，无默认 Pawn，无玩法 HUD；选择带 `MenuCamera` 标签的摄影机。开始时验证包、显示加载、延迟 0.25 秒切图；EndPlay 清理 Widget 和定时器。
- `Source/AnomalyLab/Public/AnomalyMainMenuWidget.h` 与对应 cpp：菜单命令、面板阶段、重复输入门控、键盘路由、设置草稿及保存。
- `/Game/UI/Menu/WBP_MainMenu`：可编辑 UMG 蓝图、ScaleBox 内 1600×900 布局、中文文本、状态与面板。
- `/Game/Prototype/Maps/L_MainMenu`：菜单专用实验室背景副本，移除 PlayerStart/NavMesh/原 Spawner，仅保留环境和装饰。
- `/Game/UI/Menu/Audio/`、`MenuAudio/`：原始 WAV 与导入 SoundWave；生成方法在 `Scripts/build_t19_menu_assets.py`。
- `Config/DefaultEngine.ini`：EditorStartupMap 和 GameDefaultMap 指向菜单。原 GlobalDefaultGameMode 保留，菜单地图单独 Override。
- `Config/DefaultGame.ini`：项目名称、两地图 Cook 清单、菜单 UI/音频 AlwaysCook，确保软引用 Widget 在独立包可加载。
- `Content/Prototype/Maps/L_Prototype.umap`：只显式调整原 PlayerStart 的 Pitch -90 / Yaw 0 为 Pitch 0 / Yaw -90，避免开始时看地面；原地图修改前备份 `Saved/T19Menu/Level01EntryBefore_20261010T192634/L_Prototype.umap`，前后 SHA256 和变换在 `entry_fix_report.json`。
- `Scripts/cpp_migration.py`：保留 ASCII 构建副本流程；新增源文件以 `-gather` 刷新 UBT，编译并行度 4；常规打包涵盖两张地图。
- `Scripts/package_t19_menu.py`：独立输出 `Builds/v0.3/T19Menu_<timestamp>/`，保留旧 v0.2 包。
- `Source/AnomalyLab/Private/AnomalyMenuSmoke.cpp`：仅非 Shipping 且显式 `-AnomalyMenuSmoke` 时启用的检查。普通运行不注册测试回调。

## 构建与运行

从工程根目录 `F:/AnomalyLab/我的项目3`：

```powershell
python Scripts/cpp_migration.py build-editor
python Scripts/cpp_migration.py editor --script build_t19_menu_assets.py --phase t19-menu-build
python Scripts/cpp_migration.py editor --script verify_t19_menu_assets.py --phase t19-menu-reload
python Scripts/run_t19_menu.py --width 1280 --height 720
python Scripts/run_t19_menu.py --width 1920 --height 1080
python Scripts/package_t19_menu.py
```

打开 `.uproject` 后默认显示菜单地图，Play 可试玩；也可正常启动独立包 EXE。原玩法地图可以直接打开，用于 v0.2 回归。关卡内 R 沿用原来的本关重开规则。

菜单资产生成脚本只处理菜单包：菜单地图首次从原关卡模板创建，后续只替换 `MENU_` 自有 Actor；不删除已加载 World，不保存原关卡。每次保存前备份已有菜单资产；原玩法资产在生成前后比较 SHA256。出生点修正由独立的 `fix_t19_level01_entry.py` 在验证原哈希并备份后执行，与菜单生成分开。

背景装饰箱用具名旋转参数，并依实际网格包围盒贴合底座/地面；`polish_t19_menu_staging.py` 可独立执行定位修整，最终高度记录见 `Saved/T19Menu/staging_report.json`。

## 验证记录

| 验证 | 自动断言通过 | 可见画面证据 | 人工真实操作 |
|---|---|---|---|
| 资产独立重载、编译与哈希 | 44/44 | 不适用 | 不适用 |
| Editor 游戏模式 1280×720 | 21/21 | 六张实际 D3D12 截图，已核对 | PENDING_MANUAL |
| Editor 游戏模式 1920×1080 | 21/21 | 六张实际 D3D12 截图，已核对 | PENDING_MANUAL |
| 最终独立包 1280×720 | 21/21 | 六张实际 D3D12 截图，已核对 | PENDING_MANUAL |
| 最终独立包 1920×1080 | 21/21 | 六张实际 D3D12 截图，已核对 | PENDING_MANUAL |
| v0.2 Editor 决策、终局与重开 | 47/47 | 本轮为 NullRHI，无新增画面 | 沿用用户原验收，不补造新记录 |
| v0.2 Editor 生命、追逐、死亡与异常 | 66/66 | 本轮为 NullRHI，无新增画面 | 沿用用户原基线审计结论 |
| Win64 构建/Cook/归档 | UAT ExitCode 0；46 份源/副本哈希一致 | 独立包菜单与切图如上 | PENDING_MANUAL |

21 项菜单自动检查覆盖默认菜单、无 Pawn/Coordinator、焦点、响应式布局、Slate 键盘打开设置/返回、设置草稿、指南、退出取消、防重复开始、Level01 水平视角/原 GameMode/角色/三箱、菜单清除及返回菜单后的新状态。自动驱动使用合成 Slate 键盘和按钮事件，不是人类实体按键；音效只有资产及调用验证，听感待人工。

最终证据目录：

- Editor：`Saved/T19Menu/RenderRuns/20261010T192740_1280x720/`、`20261010T192842_1920x1080/`。最后对装饰箱做贴地修整后由独立包再验证。
- 独立包：`Saved/T19Menu/RenderRuns/20261010T193430_1280x720/`、`20261010T193431_1920x1080/`。各包含 `01_main_menu.png`、`02_settings.png`、`03_field_guide.png`、`04_quit_confirmation.png`、`04b_loading.png`、`05_level01.png` 及命令、日志、JSON。
- 资产：`Saved/T19Menu/reload_report.json`，201 个唯一 Widget、46 个场景 Actor；27 个旧玩法资产保持原哈希，地图匹配出生点修正记录。
- 回归：`Saved/T18/editor_decision_report.json`、`editor_flow_report.json`；本轮报告另归档到 `Saved/T19Menu/v02_editor_*_report.json`。
- 最终打包：`Saved/T19Menu/package_report.json`、`package_source_20261010T193210.json`；原始 UAT 日志 `Saved/CppMigration/20260929T083920372566Z/t19-menu-package_20261010T113211029512Z.log`。
- 交付一致性审计：`Saved/T19Menu/delivery_audit.json`，64/64，状态 `PASS_AUTOMATED_PENDING_MANUAL`；核对当前源/构建副本哈希、最终包与两档全部 PNG 尺寸，归档本轮回归。命令 `python Scripts/audit_t19_menu_delivery.py`。

最终试玩入口：`Builds/v0.3/T19Menu_20261010T193210/Windows/AnomalyLab.exe`。移动/交付时保留整个 `Windows` 文件夹。背景修整前的 `T19Menu_20261010T192753` 仅为较早候选。

失败尝试保留在原始 journal/日志中：Widget 构造硬引用在首次生成前留下空包；已改为软引用并加入 Cook 清单。Python 枚举名及 void 返回值已按本机 API 修正。资产工具直接复制 UWorld 后切图触发旧 World 清理异常；已改为 LevelEditorSubsystem 模板创建，并对已有菜单地图重用。UBT 源文件列表缓存遗漏新 cpp 引发链接失败；已加入 `-gather`。出生点修正脚本首次因 Windows 路径分隔符不一致提前退出，没有保存地图；统一路径格式后执行成功。

## 人工待验收

- 正常鼠标点击四个菜单项，悬停颜色和音效舒适，没有焦点丢失。
- 真实键盘导航、Esc 返回和退出确认；实际确认退出到桌面。
- 应用分辨率/窗口模式/质量后生效；再次启动设置保留。
- 点击开始进入 Level01 后鼠标视角、WASD、E/Q/1/2/R 与原版本一致。
- 两档分辨率实机全屏/窗口显示，以及底噪和按钮音听感。

上述人工菜单验收状态：`PENDING_MANUAL`。用户已完成的原基线人工审计仍按其结论记录。
