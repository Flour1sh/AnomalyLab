# Low Poly Character Prototype — Codex Task Brief

## 1. 任务目标

请在 **Blender** 中程序化创建一个可用于 Unreal Engine 5 的低模人形角色原型。

这是一个 **Prototype Character**。目标不是制作高质量角色，而是验证：

```text
Codex → Blender Python → Low Poly Character → Rig-ready Mesh → FBX → Unreal Engine 5
```

角色应当适合：

- Low Poly
- Industrial Horror
- Co-op Game
- 《Lethal Company》/《R.E.P.O.》一类的低模工业恐怖氛围
- 略微笨重
- 略微滑稽
- 容易读懂轮廓
- 方便后续绑定骨骼
- 方便做简单跑步、搬运、开箱动画

不要追求写实，也不要直接复制任何现有角色设计。

## 2. 角色定位

角色设定：

> 一名为“异常货物处理公司”工作的廉价员工。

视觉关键词：

```text
Low Poly
Worker
Hazmat-inspired
Industrial
Cheap Corporate Uniform
Retro Sci-Fi
Slightly Funny
Slightly Creepy
Chunky Silhouette
```

参考的是低模、强轮廓、面部弱化、廉价工作服与工业防护感，而不是某个现有角色的具体外形。

## 3. 最终交付物

请生成：

```text
/LowPolyCharacterPrototype
├── low_poly_worker.blend
├── low_poly_worker.fbx
├── generate_worker.py
└── README_GENERATION.md
```

要求：

- 空白 Blender 工程可直接运行
- 不依赖第三方插件
- 尽量只使用 Blender Python API
- `generate_worker.py` 可以重复执行并重新生成角色
- 最终 FBX 可以导入 UE5

## 4. 人物比例

角色高度建议：

```text
Height = 1.80 m
```

整体比例：

```text
Head: slightly large
Torso: chunky
Arms: slightly long
Hands: oversized
Legs: sturdy
Feet: oversized enough for a readable silhouette
```

不要做真实人体比例。希望有一点“廉价低模恐怖游戏角色”的笨重感。

## 5. 姿势

请生成标准 **A-Pose**：

- 双臂向下约 30~45°
- 双腿自然分开
- 手掌朝身体
- 角色站直
- 左右基本对称

优先 A-Pose，而不是完全 T-Pose。

## 6. 模型结构

至少包括：

```text
Character
├── Head
├── Neck
├── Torso
├── Pelvis
├── UpperArm_L
├── LowerArm_L
├── Hand_L
├── UpperArm_R
├── LowerArm_R
├── Hand_R
├── UpperLeg_L
├── LowerLeg_L
├── Foot_L
├── UpperLeg_R
├── LowerLeg_R
├── Foot_R
└── Backpack
```

可以最终 Join 为一个 Mesh，也可以暂时保持多个 Mesh，但必须方便后续 Rig。

## 7. 建模原则

优先使用：

```text
Cube
Low-poly Cylinder
Icosphere
Simple Extrusion
Bevel
Basic Mesh Editing
```

避免：

```text
Sculpt
Subdivision-heavy workflow
High-poly anatomy
Detailed fingers
Detailed face
Complex cloth simulation
Hair strands
```

圆柱建议只用 6~8 sides，最多 12 sides。

## 8. 头部

头部使用低模头盔式造型，不做人脸。

结构：

```text
Head
├── Helmet shell
└── Front visor
```

要求：

- 头略大
- 头盔偏圆但保持 low-poly 面感
- 正面是深色面罩
- 不做眼睛、嘴、鼻子
- Visor 可以有非常轻微的蓝绿色/绿色材质倾向

目标是弱化身份，让角色看起来像“公司员工单位”。

## 9. 身体

Torso：

- 宽肩
- 略短
- 厚重
- 不追求肌肉结构

可以增加极简单的：

- 胸口工作服面板
- 公司 Badge
- 一条 Warning Stripe
- 腰部 Utility Belt

不要大量口袋、拉链、布料褶皱。

## 10. 手臂和手

手臂分成：

```text
Upper Arm
Lower Arm
Hand
```

使用低模圆柱或方柱。

手使用 **Mitten-like Hand**：

- 不做手指
- 一个块状手套即可
- 手略微放大，强化轮廓和滑稽感

## 11. 腿和靴子

腿部：

- 稍微粗
- 简单
- 支撑角色笨重感

结构：

```text
Upper Leg
Lower Leg
Boot
```

Boot 使用稍大的工业靴子，使跑步和站立时轮廓清晰。

## 12. 背部设备

添加一个简单背包：

```text
SM_Backpack_Unit
```

结构可以是：

```text
Rectangular Box
+
Small Cylinder/Tank
+
One Cable-like element
```

感觉像廉价氧气设备、电池包或公司设备。不要做复杂机械结构。

## 13. 材质

只使用简单材质，不需要复杂 PBR 贴图。

推荐材质：

```text
M_Suit
M_Dark
M_Helmet
M_Visor
M_Metal
M_Warning
```

总材质数量：

```text
<= 6
```

推荐颜色：

### Suit Main

脏黄或橙色：

```text
RGB ≈ (0.55, 0.38, 0.08)
```

或：

```text
RGB ≈ (0.60, 0.25, 0.08)
```

### Dark Cloth

```text
(0.08, 0.09, 0.10)
```

### Helmet

```text
(0.10, 0.12, 0.12)
```

### Visor

```text
(0.02, 0.04, 0.04)
```

### Metal

```text
(0.20, 0.22, 0.23)
```

### Warning Accent

```text
(0.85, 0.60, 0.05)
```

## 14. Low Poly 规范

整个角色目标：

```text
4,000 ~ 7,000 triangles
```

允许范围：

```text
3,000 ~ 10,000 triangles
```

不要超过：

```text
15,000 triangles
```

主要硬表面可以使用：

```text
Bevel Width = 0.005 ~ 0.02 m
Segments = 1
```

保持 Chunky / Angular / Readable，不要变成圆润卡通玩具。

## 15. Shading

建议混合：

```text
Flat Shading
+
少量 Smooth / Auto Smooth
```

优先保证 low-poly 面感，不要把所有东西 smooth 成塑料。

## 16. Rig-ready 要求

虽然本轮不一定需要完整 Rig，但模型必须为后续绑定做好准备：

- 肩、肘、膝附近不要明显穿插
- 手臂与身体结构要方便动画
- 腿部结构清晰
- A-Pose 标准
- 角色中心位于世界原点附近
- 脚底约在 Z = 0

如果保留多个 Mesh，请合理命名。

## 17. 可选：创建简单 Armature

如果实现稳定，可以创建：

```text
root
pelvis
spine_01
spine_02
neck
head
upperarm_l
lowerarm_l
hand_l
upperarm_r
lowerarm_r
hand_r
thigh_l
calf_l
foot_l
thigh_r
calf_r
foot_r
```

如果自动 Skinning 不可靠，不要为了 Rig 导致任务失败。优先保证 Mesh 与 FBX 完成。

## 18. 命名规范

最终角色 Mesh：

```text
SK_WorkerPrototype
```

如保留独立部件：

```text
SM_Head
SM_Torso
SM_UpperArm_L
SM_LowerArm_L
SM_Hand_L
SM_UpperArm_R
SM_LowerArm_R
SM_Hand_R
SM_UpperLeg_L
SM_LowerLeg_L
SM_Foot_L
SM_UpperLeg_R
SM_LowerLeg_R
SM_Foot_R
SM_Backpack
```

Armature：

```text
SKEL_WorkerPrototype
```

## 19. Collection

```text
LowPolyWorker
├── Body
├── Equipment
├── Rig
└── Preview
```

## 20. UE5 导出规范

角色：

```text
feet ≈ Z 0
centered near X 0, Y 0
Forward = -Y
Up = Z
```

导出前：

```text
Apply Scale
Apply Rotation
Scale = 1,1,1
```

FBX 导出：

```text
Forward = -Y
Up = Z
Apply Transform
```

导入 UE 后角色高度应约为：

```text
180 cm
```

如果有 Armature：

- 导出 Mesh + Armature
- 不导出 Preview Lights / Camera
- 避免不必要 Leaf Bones
- 检查 Bone Scale

## 21. Preview

Blender 中添加简单：

```text
Ground Plane
1 Key Light
1 Fill Light
1 Rim Light
```

只用于检查轮廓，不要做复杂电影级灯光。

## 22. generate_worker.py 建议结构

```python
clear_scene()
create_materials()
create_head()
create_torso()
create_pelvis()
create_arm(side="L")
create_arm(side="R")
create_leg(side="L")
create_leg(side="R")
create_backpack()
assemble_character()
optional_create_armature()
optional_bind_mesh()
setup_preview()
apply_transforms()
print_stats()
save_blend()
export_fbx()
```

不要把所有代码写在一个巨大函数里。

## 23. 参数化

脚本顶部设置：

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

方便下一轮快速修改比例。

## 24. 视觉重点

优先保证：

1. **轮廓**：远处也能辨认头、身体、手、脚、背包。
2. **笨重感**：不要做修长英雄角色。
3. **低模感**：不要过度 Smooth。
4. **工业工人感**：不要像普通休闲服角色。
5. **面部匿名化**：Visor 代替脸。
6. **略微滑稽**：手和鞋稍大，比例可稍夸张。

## 25. 禁止方向

严格避免：

```text
Realistic Human
Anime
Stylized Hero Character
Superhero
Military Tactical Operator
Detailed Face
Hair
Muscles
High-poly Armor
Complex Sci-Fi Spacesuit
```

目标是：

```text
Cheap Worker
Low Poly
Industrial Horror
Slightly Funny
```

## 26. 本轮不要做

```text
Facial Animation
Finger Bones
Complex IK
Cloth Simulation
Detailed UV
Texture Painting
Normal Map
Hair
Facial Rig
Animation
```

## 27. 自动检查

生成结束时输出：

```text
=== Low Poly Worker Generation Complete ===
Objects:
Meshes:
Materials:
Triangles:
Armature:
Character Height:
Blend:
FBX:
```

## 28. 优先级

### P0 — 必须完成

```text
完整人形
正确比例
A-Pose
低模
简单材质
Helmet + Visor
Work Suit
Hands
Boots
FBX Export
```

### P1

```text
Backpack
Utility Belt
Chest Panel
Simple Armature
```

### P2

```text
Automatic Skinning
Additional asymmetrical details
Improved topology
```

如果 P1 / P2 会导致任务失败，立即放弃次要功能，先保证 P0 成功。

## 29. 最终视觉目标

最终角色应该像：

> 一名穿廉价工业防护工作服的低模公司员工。

特点：

- 大一点的头盔
- 黑色面罩
- 厚重身体
- 简单工作服
- 粗手臂
- 大手套
- 粗腿
- 大工业靴
- 背后简单设备包

角色不需要精致。甚至稍微 awkward / clumsy / cheap-looking 是可以接受、甚至希望的。

整体氛围目标：

> “低模 + 怪异 + 搞笑 + 危险”的合作游戏角色。

## 30. 完成标准

- [ ] 角色高度约 180 cm
- [ ] 完整人形
- [ ] A-Pose
- [ ] Head / Torso / Arms / Legs 比例合理
- [ ] Helmet
- [ ] Dark Visor
- [ ] Work Suit
- [ ] Gloves
- [ ] Boots
- [ ] 至少一个简单 Backpack / Equipment
- [ ] Triangle Count < 15k
- [ ] Materials <= 6
- [ ] Scale = 1,1,1
- [ ] 可以导出 FBX
- [ ] FBX 可以被 UE5 正常导入
- [ ] `generate_worker.py` 可以重复运行

完成后不要继续无限细化。

先提交第一版结果，等待下一轮比例和风格修改。
