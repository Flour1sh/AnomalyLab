# v0.3 场景细节打磨

更新：2026-10-11。用户确认上一版人工测试完成后，授权保持一致建模风格、生成资产和优化关卡细节；本轮新美术版也已由用户确认人工测试完成。两次原话见 `Saved/ScenePolish/acceptance_log.md`，工作报告见 `Docs/V03_WORK_REPORT_2026-10-11.md`。

状态：模型/uasset/关卡布置、独立包、玩法回归与交付审计全部 DONE / PASS。全程本地 Blender Python、UE Python 和命令行后台构建/渲染；未调用 UE MCP、未接管屏幕、未改扩展配置。

## 这一轮改动

- 延续原有硬边低模、单段倒角、八边圆柱与旧绿/铁灰/警示黄配色。12 个原创模块共 7,748 个三角面，13 个简单材质，无新增纹理下载或联网依赖。
- 入口：回收终端、整备台、封闭金属储物箱，撤离垫改为深色底与绿色细边；终端靠墙摆放，保留移动躲避空间。
- A 分析区：带抽屉和仪表的工作台、固定样本架；B 动力区：旋钮断路器配电柜、通风百叶；C 收容区：双收容舱和监测台。
- 墙面盒板、门框、顶梁、双管/抱箍、灯具、地板分缝统一模块风格；保留绿色返回线与 A/B/C 色彩标识。候选箱台改为深色底和发光角标，降低大片实色铺地的突兀感。
- 标牌面向房间并移到墙板上方，避免反字/遮挡；颜色使用具名通道参数，修正原 Color 构造顺序造成的灯光/标牌色差。主照明下移并调整强度，保留清晰的地面与设备轮廓。

仅更新 `L_Prototype` 场景内容和新增目录，玩法 C++、Config、菜单/Legacy、箱子/背包/扫描/UI 资产均保持原字节。入口终端和固定样本只负责外观，继续由既有入口 E 规则结算，不增加新交互系统。

180 个生成对象中，14 个靠墙设备有简单 Box 碰撞；其余门框、墙板、管线、灯具和线条为装饰。门洞与原建筑碰撞继续由原场景提供，避免添加整块门框碰撞封住开口。

## 资产与复现

- 编辑源：`ScenePolishAssets/lab_details.blend`，独立 FBX：`ScenePolishAssets/fbx/`，目录预览：`ScenePolishAssets/asset_catalogue.png`，尺寸/面数：`mesh_manifest.json`。
- uasset：`Content/Prototype/Environment/ScenePolish/`（12 网格 + 13 材质）。精确模型用途及生成命令：`ScenePolishAssets/README_GENERATION.md`。
- 布置：`Scripts/build_scene_polish.py`；实际渲染：`run_scene_capture.py` / `capture_scene_polish.py`；独立重载：`verify_scene_polish.py`；最终一致性：`audit_scene_polish.py`。
- 重复构建只替换 `ScenePolishGenerated` 对象，FBX 哈希变化才重导入；每次地图/资产修改前另备份。不可重跑旧 T20 生成器，否则会覆盖后续布置与实例引用。

## 验证

| 项目 | 结果 | 证据 |
|---|---|---|
| Blender 实际 FBX 重导入 | 12/12 PASS，原点/尺度/平面着色/材质槽 | `Saved/ScenePolish/fbx_reload.json` |
| UE 独立资产/地图重载 | 53/53 PASS，三房完整导航、28 个 tile | `Saved/ScenePolish/reload_report.json` |
| 重复生成 | 180 个唯一对象，14 个实体碰撞设备 | `Saved/ScenePolish/build_report.json` |
| 既有资产保护 | 1,045 个 uasset/umap 哈希未变 | `Saved/ScenePolish/baseline.json`、最终审计 |
| 五个区域实景 | D3D12 1600×900，已核对朝向、标牌、陈设和引导线 | `Saved/ScenePolish/Views_20261011T225916/` |
| 新独立包完整连续玩法 | 151/151 PASS，默认菜单启动另 3/3；18 张实景 | `Saved/V03/Runs/20261011T230131710959_render_1280x720/` |
| 当前源码/资产/包一致性 | 149/149 PASS，111 份快照与二进制一致；Source/Config 与 1,045 个既有资产未变 | `Saved/ScenePolish/delivery_audit.json` |

区域照片用真实 SceneCapture 渲染目标生成，含保存后的关卡与照明，不运行玩法 Pawn/HUD；不是屏幕录制。完整游戏自动化另用真实 D3D12 游戏画面与合成按键验证，包含临时强制结果和故障分支，不能代替人工实际操作。本轮 UI/玩法逻辑未变，两档 UI、Legacy 历史测试保留在上一版 `FINAL_REPORT.md`；本轮不虚构新的人类体验或帧率结论。

## 新试玩入口与恢复

Win64 Development：`Builds/v0.3/AnomalyLab_RC_20261011T225958/Windows/AnomalyLab.exe`，保留整个 Windows 目录，正常双击无需测试参数。此前人工通过的 `RC_20261011T220432` 完整保留。新包构建日志：`Saved/CppMigration/20260929T083920372566Z/v03-package_20261011T145958533797Z.log`，UAT 成功；111 份源码/配置/关键资产包含全部新模块。

修改前恢复点：`Saved/ScenePolish/Checkpoint_20261011T224151/`；各次 `AssetsBefore_*` 保留本轮地图/新资产的前一版。第一次照片暴露的 FBX 朝向、标牌遮挡和原材质未预热问题已修正，早期照片/日志未删除；新终端最后靠墙调整后重新拍摄与重载。

用户对本轮交付反馈：“测试完成，你可以保留一下这一版然后记录工作报告了”。据此将 RC_20261011T225958 记录为用户总体人工测试完成并保留，不补写逐项操作、听感、帧率或用时结论。

验收后归档：`Saved/Releases/v0.3_ScenePolish_Accepted_20261011/`，包含工程源文件/资产、完整独立包、原始验证证据和 SHA-256 清单；恢复方式见其中 `README_RESTORE.md`。本次归档仅保存文件和更新文档，不重新生成资产或重打包。
