# 实验室场景细节模块

延续现有 T11E/LowPolyLab 的低面数、硬边与工业配色：平面着色、单段倒角、八边圆柱、深铁灰/旧绿/警示黄与少量屏幕发光。无需纹理下载或外部运行时服务。

## 模型构建

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python ScenePolishAssets/generate_scene_details.py
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python ScenePolishAssets/verify_fbx.py
```

输出 `lab_details.blend`、`fbx/`、`asset_catalogue.png` 和 `mesh_manifest.json`。12 个模块共 7,748 个三角面。Blender 工程采用目录展示排布，FBX 在排布前按本地底部中心原点独立导出，尺寸单位为米；UE 导入后为厘米。吊灯/管线的底部原点允许小幅倒角偏移。

| 模型 | 用途 |
|---|---|
| SM_SP_WallCassette | 带边框、铆钉的墙面盒板 |
| SM_SP_PortalFrame | 3.6 米净宽门框 |
| SM_SP_ServicePipes | 双管与抱箍 |
| SM_SP_CeilingLight | 有护栏的双管灯具 |
| SM_SP_CeilingBeam | 顶部结构梁 |
| SM_SP_ResearchBench | 抽屉、仪表、样本托盘工作台 |
| SM_SP_SpecimenRack | 固定密封样本陈列架 |
| SM_SP_PowerCabinet | 配电屏、断路旋钮与百叶 |
| SM_SP_ContainmentPod | 收容舱、观察窗与机械锁 |
| SM_SP_StorageCase | 封闭金属储物箱，与可交互木箱区别 |
| SM_SP_WallVent | 深百叶通风口 |
| SM_SP_ReturnTerminal | 入口回收终端外观 |

## UE 导入和布置

```powershell
python Scripts/cpp_migration.py editor --script build_scene_polish.py --phase scene-polish
python Scripts/run_scene_capture.py
python Scripts/cpp_migration.py editor --script verify_scene_polish.py --phase scene-polish-reload
python Scripts/package_v03.py
```

uasset 在 `/Game/Prototype/Environment/ScenePolish/`，只布置探索地图 `L_Prototype`，不重跑 T20 旧场景生成器。只替换 `ScenePolishGenerated` 标签对象，导入 FBX 用哈希判断是否需更新。每次修改地图及新资产前另存备份，基线在 `Saved/ScenePolish/baseline.json`。

装饰墙板/门框/灯具/线条不引入碰撞；14 个靠墙设备使用简单 Box 碰撞并参与导航。可交互箱子、背包、回收区域和经济规则继续使用既有权威系统，新终端/样本架为场景表现。

导入时显式匹配材质槽；UE 的 FBX 坐标转换将 Blender -Y 正面转为 +Y，布置旋转补 180 度。颜色使用具名 r/g/b/a 参数，避免 Color 结构的字段顺序误用。新材质在实际 D3D12 中编译；原 T20 材质拍摄前只在内存预热，不改已验收源资产。

## 检查与预览

独立 FBX 重导入检查原点/尺度/材质/平面着色；独立 UE 重载检查厘米尺寸、材质引用、唯一对象、原玩法位置、三房完整导航及 1,045 个既有资产哈希。场景照片由 `SceneCapture2D` 渲染目标输出，非屏幕截图，目录由 `Saved/ScenePolish/capture_report.json` 定位；正常游戏的截图由完整玩法自动化另采集。

最终打包路径从 `Saved/V03/package_report.json` 读取。完整报告见 `Docs/v0.3/SCENE_POLISH.md`。既有模型源文件、Legacy/菜单地图和玩法 C++ 不改；正常启动无需 Blender、Python 或测试参数。
