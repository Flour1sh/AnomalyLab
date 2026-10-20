# AnomalyLab

AnomalyLab 是使用 Unreal Engine 5.8 开发的第一人称实验室探索游戏原型。当前版本为 v0.5.0-rc1，包含基地与实验室切换、装备购买、扫描与拾取、撤离结算、存档及环境事件。

当前工程状态：**Engineering Verified / Awaiting Human Validation**。已有自动化验证记录，人工验收尚未完成；具体边界见 [当前状态](Docs/STATE.md)、[v0.5 交付报告](Docs/v0.5/FINAL_REPORT.md) 和 [人工测试指南](Docs/v0.5/HUMAN_TEST_GUIDE.md)。

## 获取工程

安装 Git 和 [Git LFS](https://git-lfs.com/)，然后执行：

```powershell
git lfs install
git clone https://github.com/Flour1sh/AnomalyLab.git
Set-Location AnomalyLab
git lfs pull
```

UE 资产通过 Git LFS 保存。请使用 Git 克隆并下载 LFS 对象，确保 `.uasset` 和 `.umap` 是实际资源文件。

## 开发环境与启动

- Windows、Unreal Engine **5.8**，以及该引擎要求的 Visual Studio C++ 工具链和 Windows SDK。
- 工程入口：`我的项目3.uproject`；C++ 模块及编译目标：`AnomalyLab`、`AnomalyLabEditor`。
- 工程内包含 `UnrealAgentLink` 插件源码，其许可证保留在 `Plugins/UnrealAgentLink/LICENSE`。
- `.uproject` 还启用了 `ModelContextProtocol` 和 `AllToolsets`；这两个插件没有随本仓库提供。使用相关编辑器工具时需自行安装兼容版本。若仅开发游戏且无需这些工具，可在本地禁用这两项插件后生成工程文件。

准备好依赖后，为 `.uproject` 生成 Visual Studio 工程文件，编译 **Development Editor / Win64** 的 `AnomalyLabEditor` 目标，再打开工程。默认启动地图为 `L_MainMenu`，v0.5 主流程使用 `/Game/Maps/L_Hub` 和 `/Game/Maps/L_Lab`。

工程保留了原始中文 `.uproject` 文件名。历史记录中存在该文件名引起的 MSVC/PCH 编码兼容问题，处理背景见 [C++ 迁移记录](Docs/CPP_MIGRATION.md)。需要时在独立 ASCII 路径的构建副本中使用 `AnomalyLab.uproject` 文件名，避免直接改名后破坏旧脚本的入口约定。

## 仓库内容

| 路径 | 内容 |
| --- | --- |
| `Source/` | C++ 玩法模块及构建目标 |
| `Config/` | UE 默认配置 |
| `Content/` | 地图、蓝图和游戏资源，包含外部 Actor/Object 数据 |
| `Plugins/` | 随工程提供的插件源码与资源 |
| `Scripts/` | 历史实现、资源生成、构建与验证工具 |
| `Docs/` | 架构、状态、接口与阶段报告 |
| `GameAudio/`、`MenuAudio/` | 原始音频 |
| `LowPolyCharacterPrototype/`、`LowPolyLabPrototype/`、`ScenePolishAssets/`、`T11EAssets/` | Blender 源文件、FBX、预览及生成脚本 |

`Binaries/`、`Intermediate/`、`DerivedDataCache/`、`Saved/` 和 `Builds/` 不纳入版本控制。本仓库提供源工程，不包含可直接运行的 Windows 成品包、玩家存档或本机完整备份。

历史报告中的 `F:/...`、`E:/UE_5.8`、`Saved/...` 和 `Builds/...` 指向原开发环境；相应日志、归档及可执行文件通常不在仓库中。`Scripts/` 中部分工具依赖这些本机路径和旧阶段检查点，不能直接作为全新克隆工程的通用构建入口。旧资产生成或迁移脚本可能覆盖后续修复，使用前请阅读 [维护规则](Docs/00_RULES.md)。

## 许可说明

第三方资源及插件适用各自的许可条件；`UnrealAgentLink` 的 MIT 许可仅适用于该插件。仓库没有为全部项目内容授予统一的开源许可。
