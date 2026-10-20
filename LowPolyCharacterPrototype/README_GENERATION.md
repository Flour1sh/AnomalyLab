# Low Poly Worker E-13 — Generation Guide

这是第一版原创角色源模型原型；本说明自包含生成与导出步骤。是否用于当前游戏角色以 Docs/ASSET_MAP.md 和 STATE.md 为准，不因源模型存在推定已接入。角色定位为异常货物处理公司的廉价员工，内部代号 **Worker E-13**。造型使用脏橙工装、匿名多面头盔、胸前警示斜带、夸张手套和工业靴，以及背部电池/气罐混合设备。

## Requirements

- Blender 5.1.2（本版本实际生成和验证所用版本）
- 不需要插件或第三方 Python 包

## Generate

在 PowerShell 中进入本目录后运行：

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' `
  --background --factory-startup --python .\generate_worker.py
```

脚本可以重复运行，会重新生成并覆盖以下交付物：

- `low_poly_worker.blend` — 完整、可编辑的 Blender 场景
- `low_poly_worker.fbx` — UE5 用 mesh-only FBX
- `low_poly_worker_preview.png` — 三分之四正面预览
- `low_poly_worker_back_preview.png` — 三分之四背面设备预览

## Character structure

```text
LowPolyWorker
├── Body
│   ├── SM_Head
│   ├── SM_Neck
│   ├── SM_Torso
│   ├── SM_Pelvis
│   ├── SM_UpperArm_L / R
│   ├── SM_LowerArm_L / R
│   ├── SM_Hand_L / R
│   ├── SM_UpperLeg_L / R
│   ├── SM_LowerLeg_L / R
│   └── SM_Foot_L / R
├── Equipment
│   └── SM_Backpack
├── Rig
└── Preview
```

角色保留为 17 个合理命名的分段网格。每个肢体的 Object Origin 放在对应的肩、肘、腕、髋、膝或踝关节附近，便于下一轮创建骨骼和绑定。当前版本没有 Armature，也没有自动蒙皮，以保证第一版 FBX 的稳定性。

## Parameters

可在 `generate_worker.py` 顶部修改：

```python
CHARACTER_HEIGHT = 1.80
HEAD_SCALE = 1.05
TORSO_WIDTH = 0.52
TORSO_DEPTH = 0.28
ARM_LENGTH_SCALE = 1.05
HAND_SCALE = 1.15
LEG_THICKNESS = 0.15
BOOT_SCALE = 1.15
CYLINDER_SEGMENTS = 8
BEVEL_WIDTH = 0.01
```

## UE5 import

FBX 使用 `Forward = -Y`、`Up = Z`、米制单位并应用旋转和缩放导出。推荐：

- Import Type: Static Mesh
- Combine Meshes: Off（保留各分段及名称）
- Import Uniform Scale: 1.0
- Convert Scene / Convert Scene Unit: On
- Import Materials: 可选

材质只包含 6 个共享槽：`M_Suit`、`M_Dark`、`M_Helmet`、`M_Visor`、`M_Metal`、`M_Warning`。若下一轮加入 Armature 和权重，再改为 Skeletal Mesh 导出。

## Scope of this version

本轮完成 P0 和背包、腰带、胸板等 P1 造型。没有制作动画、自动蒙皮、手指、复杂 IK、UV 贴图或高模细节。
