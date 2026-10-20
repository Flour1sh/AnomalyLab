# v0.3 构建、自动化和人工测试

所有命令从 `F:/AnomalyLab/我的项目3` 运行。需要本机 `E:/UE_5.8` 与 Python；无 UE MCP、屏幕接管或在线运行时服务。

```powershell
python Scripts/cpp_migration.py build-editor
python Scripts/cpp_migration.py editor --script build_v03_loot.py --phase v03-t21
python Scripts/cpp_migration.py editor --script build_v03_ui.py --phase v03-t22
python Scripts/cpp_migration.py editor --script build_v03_feedback.py --phase v03-t24
python Scripts/cpp_migration.py editor --script polish_v03_ui.py --phase v03-ui-polish
python Scripts/warm_v03.py
python Scripts/cpp_migration.py editor --script verify_v03_assets.py --phase v03-reload
python Scripts/run_v03.py
python Scripts/run_v03.py --from-menu --render --width 1280 --height 720
python Scripts/run_v03.py --from-menu --render --width 1920 --height 1080 --mute
python Scripts/run_v03.py --strategy conservative
python Scripts/run_v03.py --strategy greedy
python Scripts/run_v03.py --strategy random
python Scripts/run_t18.py editor stats
python Scripts/run_t18.py editor decision
python Scripts/run_t18.py editor flow
python Scripts/package_v03.py
```

不要同时运行构建/部署和使用同一 DLL 的 UE 游戏进程。材质预热必须使用实际 D3D12；NullRHI 资产生成不等于着色器渲染检查。若重新构建探索 HUD，应在 UI 构建后再运行反馈构建，以补上遮罩和准星。

独立包路径读 `Saved/V03/package_report.json` 的 `exe`。将它作为 `--exe` 参数，可重跑 `run_v03.py` 和 `run_t19_menu.py`，不要传 `-DisablePlugins` 给独立包。正常试玩双击该 EXE，无需测试参数；需保留整个 Windows 文件夹。

最终包验证命令：

```powershell
$package = Get-Content Saved/V03/package_report.json -Raw | ConvertFrom-Json
python Scripts/run_v03.py --from-menu --render --exe $package.exe
python Scripts/run_v03.py --from-menu --render --width 1920 --height 1080 --mute --exe $package.exe
python Scripts/run_t19_menu.py --exe $package.exe
python Scripts/run_t19_menu.py --width 1920 --height 1080 --exe $package.exe
python Scripts/run_t18.py packaged stats --map /Game/Prototype/Maps/L_LegacyPrototype --exe $package.exe
python Scripts/run_t18.py packaged decision --map /Game/Prototype/Maps/L_LegacyPrototype --exe $package.exe
python Scripts/run_t18.py packaged flow --map /Game/Prototype/Maps/L_LegacyPrototype --exe $package.exe
python Scripts/audit_v03_delivery.py
```

渲染套件依次运行；`--from-menu` 从实际默认菜单开始，点开始游戏后由玩法驱动接续，覆盖同局扫描、携带 Loot、自然存活威胁、回入口、结算和重开。其他边界场景使用临时强制结果及传送布置；不用这些参数时不会创建测试驱动。

## 人工操作清单（自动化不能代替）

- 菜单真实鼠标/键盘开始、设置和退出；进入 Level01 无菜单残留。
- WASD/鼠标/空格正常，辨认 A/B/C 与绿色入口路线；分别进入三房。
- 按住 Q 一秒扫描，松开/移开/切换工具取消；对未知箱读数不能当保证。
- E 开箱，一箱打开、另外两箱锁定；物品发光、按 E 拾取，钱只显示为携带价值。
- 拾取四件后满格，第五件留在地上；1 继续仍保留携带物品。
- 2 选择撤离后实际走到入口、按 E；成功后带出金额与物品一致。空包也可撤离。
- 遭遇威胁时看方向、倒计时、红光；移动躲避或受伤死亡。二次收容后必须回入口。
- 死亡显示丢失价值、收入 0；结算后 R 重开，所有状态重置。
- 两档分辨率中文/布局与静音可读性；实际听取扫描、开箱、拾取、预警、追逐、受伤和撤离音效。
- 记录保守/贪婪/随机真实试玩的用时、带出价值、死亡、扫描次数与卡点。机器人数据不能证实人类 3–5 分钟节奏。

原始运行证据在 `Saved/V03/Runs/`；构建/失败日志在 `Saved/CppMigration/20260929T083920372566Z/`。恢复点见 `Saved/V03/checkpoint_path.txt`；每个资产生成器另存修改前备份。完整结论以 `Docs/v0.3/FINAL_REPORT.md` 为准。
