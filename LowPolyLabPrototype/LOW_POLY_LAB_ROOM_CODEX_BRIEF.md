# Low Poly Lab Room Prototype — Codex Task Brief

## 1. 任务目标

请在 **Blender** 中程序化创建一个可用于 Unreal Engine 5 的低模实验室 / 工业设施房间内部。

目标风格：

- Low Poly
- Industrial
- Retro Sci-Fi
- Horror Facility
- 廉价公司实验设施
- 视觉感觉接近《Lethal Company》《R.E.P.O.》这类低模工业恐怖游戏
- 不追求写实
- 不要高精度雕刻
- 不需要复杂贴图
- 依靠简单几何体、比例、灯光、颜色和少量工业细节形成风格

这是一个 **Prototype Asset Test**。

当前最重要的目标是：

> 验证 Codex 是否可以通过 Blender Python 自动生成一套风格统一、可以直接导入 UE5 的低模场景资产。

---

# 2. 最终交付物

请最终生成：

```text
/LowPolyLabPrototype
│
├── low_poly_lab_room.blend
├── low_poly_lab_room.fbx
├── generate_lab_room.py
└── README_GENERATION.md
```

其中：

### low_poly_lab_room.blend
完整 Blender 工程。

### low_poly_lab_room.fbx
可以直接导入 Unreal Engine 5 的 FBX。

### generate_lab_room.py
完整 Blender Python 生成脚本。

要求：

- 可以在一个空白 Blender 工程中重新运行
- 一键重建整个场景
- 不依赖手动编辑步骤
- 不依赖额外插件
- 尽量只使用 Blender 自带 Python API

### README_GENERATION.md
简单说明：

- 如何运行脚本
- Blender 版本
- 如何重新生成
- 如何修改主要参数
- 如何导出 UE5

---

# 3. 房间总体设计

先只生成 **一个完整房间内部**。

不要生成整栋实验室。

房间定位：

> 一间属于廉价异常物品处理公司的地下实验室 / 仓储检测室。

它应该看起来：

- 有点旧
- 有点脏
- 有工业设施
- 有复古电脑
- 有管道
- 有箱子
- 有货架
- 有一扇工业门
- 有简单实验设备
- 但整体模型非常低模

---

# 4. 房间尺寸

使用真实世界比例。

Blender 单位：

```text
Metric
1 Blender Unit = 1 meter
```

房间大约：

```text
Width  = 8 m
Length = 10 m
Height = 4 m
```

建议：

```text
X = 8 m
Y = 10 m
Z = 4 m
```

---

# 5. 房间结构

至少包括：

```text
Room
├── Floor
├── Ceiling
├── Wall_Left
├── Wall_Right
├── Wall_Back
└── Wall_Front
```

Front Wall 上留一扇门。

不要完全把房间封死导致编辑困难。

可以让：

```text
Ceiling
```

作为单独 Mesh，方便在 UE 中隐藏。

---

# 6. 门

创建一个低模工业门：

```text
SM_Door_Industrial
```

尺寸约：

```text
Width  = 1.6 m
Height = 2.6 m
Depth  = 0.15 m
```

造型：

- 厚重
- 方形
- 简单
- 略微向内凹
- 边缘有黄色警戒条
- 中间可以有一个小观察窗
- 一侧有一个门禁按钮

不要做复杂机械结构。

重点是：

> 一眼看起来像工业设施 / 实验室门。

---

# 7. 地板

地板不要只是纯平 Cube。

建议增加非常简单的结构：

```text
Floor
├── Main Floor
├── Metal Strip
├── Drain
└── Warning Area
```

可以使用：

- 大块深灰色地面
- 若干金属条
- 一个简单排水口
- 黄黑警示区域

不要使用复杂贴图。

---

# 8. 墙体

墙面需要有一定工业感。

可以增加：

```text
Wall Panel
Wall Support Beam
Cable
Pipe
Vent
Warning Sign
```

但不要做满。

推荐原则：

```text
70% 空白墙面
30% 工业细节
```

避免整个房间太杂乱。

---

# 9. 必须生成的 Props

至少生成以下物体。

---

## 9.1 工业货架

```text
SM_Shelf_Industrial
```

数量：

```text
2
```

结构：

- 四根柱子
- 3~4层横板
- 低模
- 深灰 / 灰绿色
- 可以有轻微不对称

其中一个货架可以放：

- 箱子
- 小垃圾
- 金属零件

---

## 9.2 木箱 / 工业箱

创建：

```text
SM_Crate
```

至少：

```text
3 variants
```

例如：

```text
SM_Crate_A
SM_Crate_B
SM_Crate_C
```

差异可以仅仅是：

- 尺寸
- 顶盖
- 金属边框
- 警示颜色

不要制作复杂纹理。

---

## 9.3 实验工作台

```text
SM_LabDesk
```

尺寸约：

```text
Width = 2.0 m
Depth = 0.8 m
Height = 0.9 m
```

上面放：

```text
Monitor
Keyboard-like slab
Small container
Control box
```

整体保持低模。

---

## 9.4 复古电脑

创建：

```text
SM_RetroComputer
```

风格：

- CRT Monitor
- 厚屏幕
- 大边框
- 方形
- 不要现代超薄显示器
- 屏幕发绿色或蓝绿色 Emissive

屏幕可以只使用单色材质。

不需要真正 UI。

---

## 9.5 储物柜

```text
SM_Locker
```

数量：

```text
2~3
```

特点：

- 高而窄
- 四方形
- 简单门缝
- 3个横向通风槽
- 大号把手
- 灰绿色

不要 Boolean 出过多细节。

---

## 9.6 管道

创建模块：

```text
SM_Pipe_Straight
SM_Pipe_Corner
SM_Pipe_Junction
```

至少在房间顶部沿墙布置一组管道。

要求：

- 粗
- 低分段
- 圆柱 sides 建议 8 或 12
- 不要 32/64 sides

---

## 9.7 通风口

```text
SM_Vent
```

放置在墙面高处。

简单：

- 外框
- 内部 4~6 条横片

即可。

---

## 9.8 天花板灯

```text
SM_CeilingLight
```

数量：

```text
3~4
```

长条工业灯。

形状：

```text
Rectangle Housing
+
Emissive Strip
```

不要复杂灯罩。

---

## 9.9 红色警报灯

```text
SM_AlarmLight
```

放在门附近。

非常简单：

```text
Base
+
Low-poly red lamp
```

---

## 9.10 垃圾

创建少量简单垃圾：

```text
SM_TrashCan
SM_ScrapMetal_A
SM_ScrapMetal_B
SM_BrokenBox
```

全部使用非常简单的几何体。

---

# 10. 场景布局

建议布局如下：

```text
 ------------------------------------------------
|                                                |
| Pipe ===============================           |
|                                                |
| [Shelf]                         [Locker]        |
| [Shelf]                         [Locker]        |
|                                                |
|                                                |
|                 [CRATE]                        |
|                                                |
|                                                |
| [Lab Desk]                                     |
| [Computer]                         [Trash]      |
|                                                |
|                    INDUSTRIAL DOOR              |
 ------------------------------------------------
```

房间中央留出较大空间。

原因：

以后游戏中中央可能放置：

```text
Loot Box
Anomaly Box
Auction Crate
Enemy Spawn
```

所以：

> 不要把 Props 堆在房间正中央。

---

# 11. 核心交互预留区域

房间中央留下大约：

```text
3m × 3m
```

空区域。

这里未来会放：

```text
BP_LootContainer
```

暂时可以放一个测试箱子：

```text
SM_TestLootCrate
```

尺寸：

```text
1m × 1m × 1m
```

测试箱子需要明显一点。

可以使用：

- 黄色
- 橙色
- 红色小灯

让它成为视觉中心。

---

# 12. Low Poly 建模规范

这是非常重要的部分。

---

## 12.1 不要过度细分

例如圆柱：

```text
6
8
12
```

边即可。

不要默认：

```text
32
64
```

---

## 12.2 使用简单几何体

优先：

```text
Cube
Cylinder
Plane
Bevel
Extrude
Inset
```

尽量少使用：

```text
复杂 Boolean
Subdivision Surface
Sculpting
高密度 Mesh
```

---

## 12.3 Bevel

所有主要 Props 可以使用非常轻微的 Bevel。

例如：

```text
Bevel Width = 0.01 ~ 0.04 m
Segments = 1
```

不要做圆润卡通玩具感。

我们需要：

> 简单，但是有一点工业边缘处理。

---

## 12.4 面数

整个房间 Prototype：

```text
目标 < 100,000 triangles
```

最好：

```text
30,000 ~ 70,000 triangles
```

单个普通 Prop：

```text
100 ~ 3000 triangles
```

大型 Props：

```text
尽量 < 5000 triangles
```

---

# 13. 材质规范

不要生成复杂 PBR 贴图。

第一版只使用：

> Simple Material Palette

推荐颜色：

### Dark Metal

```text
RGB approximately:
0.10
0.12
0.13
```

### Industrial Gray

```text
0.25
0.27
0.27
```

### Dirty Green

```text
0.22
0.30
0.25
```

### Warning Yellow

```text
0.85
0.60
0.05
```

### Warning Red

```text
0.65
0.05
0.04
```

### Screen Green

```text
0.05
0.70
0.35
```

### Cold Light

```text
0.55
0.75
0.90
```

---

# 14. 材质数量

请尽量复用材质。

总材质数建议：

```text
< 10
```

例如：

```text
M_DarkMetal
M_GrayMetal
M_DirtyGreen
M_WarningYellow
M_Red
M_Black
M_Screen
M_Light
```

---

# 15. Shader 参数

普通材质：

```text
Metallic = 0.0 ~ 0.7
Roughness = 0.6 ~ 0.9
```

不要做大量镜面反射。

这是一个：

> 脏、廉价、旧的工业环境。

---

# 16. 灯光

Blender 中可以加简单灯光做 Preview。

至少：

```text
3 Ceiling Lights
1 Red Alarm Light
1 weak fill light
```

推荐：

- 房间总体偏暗
- 冷色顶灯
- 门附近红色警报灯
- 角落稍暗

不要做：

- 强烈电影级打光
- 大量彩色 Neon
- Cyberpunk 灯光

目标不是赛博朋克。

目标是：

> 廉价工业设施。

---

# 17. 风格限制

请严格避免以下风格：

```text
❌ Clean Sci-Fi
❌ Cyberpunk
❌ NASA
❌ Star Wars
❌ White Laboratory
❌ Photorealistic UE5 Environment
❌ High-poly machinery
❌ Extreme detail
```

目标：

```text
✅ Low Poly
✅ Industrial
✅ Slight Horror
✅ Retro Technology
✅ Dirty Facility
✅ Cheap Corporate Lab
✅ Simple Shapes
✅ Strong Silhouette
```

---

# 18. 可读性原则

即使模型简单，也应该做到：

### 一眼能看懂是什么。

比如：

电脑：

```text
大 CRT
+
大边框
+
明显屏幕
```

门：

```text
厚重
+
警告条
+
按钮
```

储物柜：

```text
高矩形
+
门缝
+
通风槽
```

不要依赖贴图表达物体类型。

---

# 19. Blender Object Naming

严格使用：

```text
SM_Wall_A
SM_Wall_B
SM_Floor
SM_Ceiling

SM_Door_Industrial

SM_Shelf_A
SM_Shelf_B

SM_LabDesk
SM_RetroComputer

SM_Locker_A
SM_Locker_B

SM_Pipe_Straight
SM_Pipe_Corner

SM_Vent

SM_Crate_A
SM_Crate_B
SM_Crate_C

SM_TrashCan

SM_CeilingLight_A
SM_CeilingLight_B
SM_AlarmLight

SM_TestLootCrate
```

如果生成更多物体，也统一：

```text
SM_Name
```

---

# 20. Collection 结构

Blender Collection：

```text
LowPolyLab
│
├── Architecture
│
├── Props
│
├── Pipes
│
├── Lights
│
└── Gameplay
```

其中：

### Architecture

```text
Wall
Floor
Ceiling
Door
```

### Props

```text
Shelf
Desk
Computer
Locker
Crate
Trash
```

### Pipes

```text
Pipe
Vent
```

### Gameplay

```text
SM_TestLootCrate
```

---

# 21. Pivot / Origin 规范

为了未来 UE 使用：

所有 Props：

```text
Origin = Bottom Center
```

墙体：

```text
Origin = Bottom / Logical Corner
```

门：

```text
Origin = Door Hinge Side
```

这样未来可以直接旋转开门。

---

# 22. Transform

导出前：

```text
Apply Rotation
Apply Scale
```

确保：

```text
Scale = 1,1,1
```

尽量保持：

```text
Rotation = 0,0,0
```

---

# 23. UE5 导出要求

FBX：

```text
Forward = -Y
Up = Z
Apply Transform
```

场景尺寸必须正确。

确保一个：

```text
2 m door
```

导入 UE 后真的约等于人物高度。

---

# 24. 不需要完成的东西

这一版不要浪费时间做：

```text
❌ Character
❌ Spider Monster
❌ Interaction Blueprint
❌ Door Animation
❌ Complex UV
❌ Texture Painting
❌ Decals
❌ Dirt Textures
❌ Damage System
❌ Gameplay
❌ Niagara
❌ Perfect Lighting
```

只做：

> 房间模型 + Props + 简单材质 + Preview Lighting。

---

# 25. 脚本实现要求

请优先写：

```python
generate_lab_room.py
```

脚本结构建议：

```python
clear_scene()

create_materials()

create_room()
create_door()

create_shelf()
create_desk()
create_retro_computer()
create_lockers()

create_pipes()
create_vent()

create_crates()
create_trash()

create_ceiling_lights()
create_alarm_light()

create_test_loot_crate()

setup_preview_lighting()

organize_collections()
apply_transforms()

save_blend()
export_fbx()
```

不要把所有逻辑写在一个 1000 行函数里。

请拆函数。

---

# 26. 参数化

请在脚本顶部设置：

```python
ROOM_WIDTH = 8.0
ROOM_LENGTH = 10.0
ROOM_HEIGHT = 4.0

BEVEL_WIDTH = 0.02

PIPE_RADIUS = 0.12
PIPE_SEGMENTS = 8
```

以及主要颜色。

这样以后可以快速改整体风格。

---

# 27. 生成过程

Codex 请自行：

1. 创建 Blender Python Script
2. 运行脚本
3. 检查 Blender Console 是否报错
4. 如果报错，修复
5. 重新运行
6. 确认所有物体都正确生成
7. 保存 `.blend`
8. 导出 `.fbx`

不要只生成脚本然后停止。

---

# 28. 自动检查

生成结束后输出统计：

```text
Objects:
Meshes:
Materials:
Triangles:
Lights:
```

例如：

```text
=== Low Poly Lab Generation Complete ===

Objects: 47
Meshes: 39
Materials: 8
Triangles: 42,680
Lights: 5

Blend:
./low_poly_lab_room.blend

FBX:
./low_poly_lab_room.fbx
```

---

# 29. 如果无法直接控制 Blender

如果当前 Codex 环境无法直接打开或控制 Blender：

请仍然：

1. 完整编写 `generate_lab_room.py`
2. 确保可以从命令行执行

例如：

```bash
blender --background --python generate_lab_room.py
```

并让脚本自动：

```text
Create Scene
→ Save Blend
→ Export FBX
→ Exit
```

---

# 30. 优先级

如果工作量过大，请按以下优先级执行：

## P0

必须完成：

```text
Room
Door
Floor
Ceiling
Simple Materials
Lighting
FBX Export
```

## P1

其次：

```text
Shelf
Desk
Retro Computer
Locker
Crates
```

## P2

最后：

```text
Pipes
Vent
Trash
Alarm Light
Extra Details
```

确保首先产出一个完整可看的房间，不要因为小 Prop 没完成导致最终没有结果。

---

# 31. 最终视觉目标

最终打开 Blender 时应该看到：

> 一个面积不大的、昏暗的、低成本工业实验室房间。

房间中：

- 墙面灰暗
- 顶部有粗管道
- 一侧有货架
- 一侧有复古 CRT 实验电脑
- 有几个储物柜
- 地面散落少量箱子和废物
- 门附近闪着红色警报灯
- 中央有一个明显的异常货物箱
- 整个场景低模、简单、容易读懂

如果模型单独拿出来不够精致，没有关系。

最重要的是：

> 所有资产放在一起时风格统一，并且能立即让玩家理解这里是一个“廉价、危险、处理异常物品的公司实验设施”。

---

# 32. 本轮任务完成标准

这次 Prototype 达到以下标准即可停止：

- [ ] Blender 可以正常打开工程
- [ ] 房间比例正确
- [ ] 有完整墙 / 地 / 天花板
- [ ] 有工业门
- [ ] 有至少 5 类 Props
- [ ] 有管道或通风结构
- [ ] 有低模复古电脑
- [ ] 中央有测试货箱
- [ ] 材质数量 < 10
- [ ] 场景整体明显是 Low Poly
- [ ] 可以成功导出 FBX
- [ ] FBX 可以被 UE5 正常导入
- [ ] 生成脚本可以重新运行

完成这些以后，不要继续无限增加细节。

先把结果交付，之后再进行第二轮风格修改。
