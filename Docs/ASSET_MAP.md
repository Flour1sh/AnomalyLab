# PROTOTYPE ASSET MAP

Use these exact locations instead of scanning the full Content directory. Update this file when a final asset is selected or a planned asset is created.

## v0.3 T19 — Main menu / Level01 entry (2026-10-10)

```text
Default startup map: /Game/Prototype/Maps/L_MainMenu
Gameplay Level01: /Game/Prototype/Maps/L_Prototype
Menu Widget: /Game/UI/Menu/WBP_MainMenu
Menu GameMode: /Script/AnomalyLab.AnomalyMenuGameMode
Menu PlayerController: /Script/AnomalyLab.AnomalyMenuPlayerController
Widget native parent: /Script/AnomalyLab.AnomalyMainMenuWidget
Audio: /Game/UI/Menu/Audio/S_MenuHover
       /Game/UI/Menu/Audio/S_MenuSelect
       /Game/UI/Menu/Audio/S_MenuRoomTone
```

菜单只使用自身场景和 Widget；Level01 保留原 Blueprint GameMode/Controller/Character。原地图 PlayerStart 朝向已单独修正，备份见 `Saved/T19Menu/entry_fix_report.json`。运行、构建及恢复步骤见 `Docs/v0.3/T19_MAIN_MENU.md`。

## v0.3 T20 — Exploration build (2026-10-11, gameplay acceptance pending)

```text
Level01 (same menu entry): /Game/Prototype/Maps/L_Prototype
Preserved old map: /Game/Prototype/Maps/L_LegacyPrototype
Passive HUD: /Game/UI/WBP_ExplorationPrompt
HUD native parent: /Script/AnomalyLab.AnomalyExplorationWidget
Generated cube/materials: /Game/Prototype/Environment/T20/
```

`BP_BoxSpawner` 原生默认 LegacyPrototype，探索地图实例为 Exploration；旧箱子/定义/Scanner 资产保留。角色仅改 T06Restart 重载当前地图。构建及恢复见 `Docs/v0.3/T20_EXPLORATION.md`。

## Project build

当前 Runtime C++ 模块：`F:/AnomalyLab/我的项目3/Source/AnomalyLab/`。Box、Wallet、Spider、Spawner 及定义蓝图现继承模块原生类，迁移细节见 `Docs/CPP_MIGRATION.md`。打包使用 `Scripts/cpp_migration.py`，旧 `build_t09.py` 不包含 Source。

```text
Project:
F:/AnomalyLab/我的项目3/我的项目3.uproject

Engine:
E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe

Commandlet:
E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe
```

## T11 — Built 2026-09-27; user gameplay acceptance 2026-09-30

```text
/Game/Prototype/Data/Boxes/BP_AnomalyBoxDefinition
/Game/Prototype/Data/Boxes/DA_Box_Safe
/Game/Prototype/Data/Boxes/DA_Box_Risky
/Game/Prototype/Data/Boxes/DA_Box_Unknown
/Game/Prototype/Data/Boxes/DA_Box_UnknownSafe
/Game/Prototype/Data/Boxes/DA_Box_UnknownMedium
/Game/Prototype/Data/Boxes/DA_Box_UnknownRisky
```

迁移后修改：`/Game/Anomalies/Containers/BP_AnomalyBox`、`/Game/Anomalies/Containers/BP_BoxSpawner`、`/Game/Anomalies/Creatures/BP_Spider`、`/Game/Core/Components/BPC_Wallet`、上列定义类与六个数据资产。
DataAssets replace the planned Struct/DataTable because stock Python cannot author the struct fields on this installation.
No Struct/DataTable was saved. `Scripts/RUN_T11.ps1` 是迁移前历史入口，不可在当前原生蓝图上重跑；当前入口见 `Docs/CPP_MIGRATION.md`。

## T11E — Built 2026-09-30; user acceptance 2026-10-02

```text
/Game/Prototype/Equipment/T11E/SM_Scanner_Metal
/Game/Prototype/Equipment/T11E/SM_Scanner_Bio
/Game/Prototype/Equipment/T11E/SM_Scanner_Matter
/Game/Prototype/Equipment/T11E/SM_Gun_Placeholder
/Game/Prototype/Environment/BoxClues/SM_Crate_MetalBrace
/Game/Prototype/Environment/BoxClues/SM_Crate_WarningMarker
/Game/Prototype/Environment/BoxClues/SM_Crate_WearPatch
```

`BP_FirstPersonCharacter` 挂 `T11EEquipment` 原生组件并引用四个手持模型；`BP_AnomalyBox` 引用三种箱体线索。源文件和重建方法见 `T11EAssets/generate_t11e.py`、`Scripts/RUN_T11E.md`。现有箱体骨骼网格、开箱动画与输入映射资产未改动。

## First Person Template

```text
Character:
/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter

Player Controller:
/Game/FirstPerson/Blueprints/BP_FirstPersonPlayerController

GameMode:
/Game/FirstPerson/Blueprints/BP_FirstPersonGameMode

Existing Mapping Context:
/Game/Input/IMC_Default

Existing Template Map:
/Game/FirstPerson/Lvl_FirstPerson
```

Do not move or rename these assets. Do not modify existing movement bindings without a current Ticket requirement.

## Wooden Crate

```text
Skeletal Mesh:
/Game/AnimatedWoodenCrateV1/Meshes/SKM_WoodenCrate

Opening Animation:
/Game/AnimatedWoodenCrateV1/Animations/AS_WoodenCrateOpen

Opening Sound:
/Game/AnimatedWoodenCrateV1/Audio/SC_WoodenCrateOpen

Gold Mesh:
/Game/AnimatedWoodenCrateV1/Meshes/SM_WoodenCrateGoldIngots
```

Reference these assets from project-owned Blueprint. Do not edit asset-pack originals.

## Trash

```text
Chair Mesh:
/Game/SciFiWorld/Meshes/SM_Chair08
```

## Spider — Selected T05 Mesh

Selected through offline Python mesh comparison. Visual height is 90 cm.
T05 chase behavior was accepted by the user on 2026-09-20.

```text
/Game/SciFiWorld/Meshes/SM_CreatureAlien06-Pose2
```

## Low Poly Lab

```text
FBX Source:
F:/AnomalyLab/我的项目3/LowPolyLabPrototype/low_poly_lab_room.fbx

Blender Source:
F:/AnomalyLab/我的项目3/LowPolyLabPrototype/low_poly_lab_room.blend

Generation Notes:
F:/AnomalyLab/我的项目3/LowPolyLabPrototype/README_GENERATION.md

Unreal Import Destination:
/Game/Prototype/Environment/LowPolyLab/

Prototype Map:
/Game/Prototype/Maps/L_Prototype
```

## Implemented T06 Assets — Accepted 2026-09-22

```text
/Game/Core/Input/IA_Restart
/Game/Anomalies/Containers/BP_BoxSpawner
```

Python build also modifies `IMC_Prototype`, `BP_FirstPersonCharacter`,
`WBP_PrototypeHUD`, and `L_Prototype`. The previously empty
`EPrototypeRoundState` now contains Ready / Revealing / OutcomeActive / Ended.
Current function/event contracts are documented in `Docs/01_CONTRACTS.md`. T06 has user-confirmed acceptance.

## Implemented T00 Assets

```text
/Game/Core/Debug/BFL_PrototypeLog
/Game/Core/Types/EAnomalyOutcome
/Game/Core/Types/EPrototypeRoundState
/Game/Prototype/Environment/LowPolyLab/
/Game/Prototype/Maps/L_Prototype
```

## Implemented T01/T02 Assets

```text
/Game/Interaction/BPI_Interactable
/Game/Core/Components/BPC_Interaction
/Game/Core/Input/IA_Interact
/Game/Core/Input/IMC_Prototype
/Game/Anomalies/Containers/BP_AnomalyBox
```

`BP_AnomalyBox` references the Wooden Crate assets listed above. T06 replaces its
placed test instance with `BP_BoxSpawner` at the same transform (`Z = 50 cm`).

## Implemented T04 Assets

Accepted by the user after manual testing on 2026-09-17.

```text
/Game/Core/Components/BPC_Wallet
/Game/Anomalies/Loot/BP_Loot_HighValue
/Game/Anomalies/Loot/BP_Loot_Trash
/Game/UI/WBP_PrototypeHUD
```

T04 also integrates these assets into the existing `BP_FirstPersonCharacter` and `BP_AnomalyBox`.

## Implemented T05 Assets — Accepted 2026-09-20

```text
/Game/Anomalies/Creatures/BP_Spider
```

T05 build, chase repair, automated checks and user acceptance are complete.
`CreatureSpawnPoint` is relative `(250, -300, -3)`, world `(250, -300, 47)`
for a box at the pedestal transform. Current Blueprint implementation details are in `Docs/01_CONTRACTS.md`.

## Current T10 source and packaged baseline

T10 modifies the existing `/Game/Anomalies/Creatures/BP_Spider`; no duplicate creature,
skeleton or animation sequence was added. Functions: T10FacePlayer / T10AnimateBody.
User confirmed T10 testing complete on 2026-09-24; see STATE and 01_CONTRACTS for current facts.
The package `Builds/T09/20260923T090604Z/Windows/AnomalyLabT09.exe` predates T10.
## T12 增量（2026-10-02 构建及用户验收通过）

- `/Game/Core/Components/BPC_Scanner`：`UAnomalyScannerComponent` Blueprint，300 cm / 1 s，引用扫描面板。
- `/Game/UI/WBP_ScanPanel`：`UAnomalyScanWidget`，ScanSummary/ScanHint/ScanProgress 三个原生绑定控件。
- `/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter`：新增 `T12Scanner` 组件，保留 `T11EEquipment`、原 HUD、输入与移动。
- Python 构建/重载入口：`Scripts/build_t12_assets.py`、`Scripts/verify_t12_assets.py`；备份与报告：`Saved/T12/`。



## v0.3 T21–T24

- `/Game/Prototype/Data/Items/DA_LabChip`：实验芯片；`DA_AnomalyCore`：异常核心；`DA_SampleCanister`：密封样本；`DA_SpentBattery`：废旧电池（固定 $3）。同目录有四个独立基础网格与发光材质。
- `/Game/Prototype/Audio/S_ScanStart`、`S_ScanComplete`、`S_Pickup`、`S_Reveal`、`S_Warning`、`S_Threat`、`S_Damage`、`S_Extract`、`S_Containment`。源 WAV 在 `GameAudio/`，由 Python 确定性合成。
- `/Game/UI/WBP_ExplorationPrompt` 扩展背包、通知、准星和受伤遮罩；旧 WBP_PrototypeHUD 在探索模式隐藏，原对象保留供旧 Blueprint 适配。Legacy 继续显示旧 HUD。
- 入口及资产引用仍位于 `L_Prototype` 的单个 BP_BoxSpawner 实例；不更改 Legacy 地图数据。原生 Pickup/Inventory 不需要空壳蓝图，直接使用 C++ 类。

## v0.3 场景细节打磨（2026-10-11）

- `/Game/Prototype/Environment/ScenePolish/`：12 个 `SM_SP_` 模块（WallCassette、PortalFrame、ServicePipes、CeilingLight、ResearchBench、SpecimenRack、PowerCabinet、ContainmentPod、StorageCase、WallVent、ReturnTerminal、CeilingBeam），13 个 `M_SP_` 材质。
- 编辑源 `ScenePolishAssets/lab_details.blend`、独立导出 `ScenePolishAssets/fbx/`；模块用途、尺度与命令见 `ScenePolishAssets/README_GENERATION.md`。
- `L_Prototype` 新增 `ScenePolishGenerated` 标签对象，仅 14 个靠墙设备有碰撞；箱子/玩家/撤离位置和原建筑碰撞保持。菜单与 Legacy 地图未改。
- 实施/证据/新包入口：`Docs/v0.3/SCENE_POLISH.md`；检查点与报告：`Saved/ScenePolish/`。
# v0.4 T26 additions (2026-10-12)

- `/Game/Prototype/Data/Regions/DA_Region_A`、`DA_Region_B`、`DA_Region_C`：原生 `UAnomalyRegionDefinition`，重建 `Scripts/build_t26_assets.py`，数值源 `Scripts/t26_data.py`。
- `/Game/Prototype/Maps/L_Prototype`：仅现有 Coordinator 实例 RegionRules/use_region_rules；原场景几何/导航/音频保持。
- `/Game/UI/WBP_ExplorationPrompt`：增量增加 RegionText / RegionBacking，不重建原控件树。
- 新原生 `AnomalyRegionDefinition.h/.cpp`；非 Shipping 显式 `-AnomalyT26Smoke` 测试驱动 `AnomalyRegionSmoke.cpp`。正常启动没有此驱动。
- 新构建报告 `Saved/V04/T26/package_report.json`，新包目录 `Builds/v0.4/AnomalyLab_T26_*/Windows`，仅 T26 检查点，不是整个 v0.4 发布版。

