# v0.4 Initialization + T26 reproduction

从 `F:/AnomalyLab/我的项目3` 后台运行；不使用 UE MCP/屏幕接管。UE 命令可能需要已获准的受限环境外执行，exit=0 且无报告不算成功。编译/部署时关闭使用该 Editor DLL 的 UE 进程。

```powershell
python Scripts/cpp_migration.py build-editor
python Scripts/cpp_migration.py editor --script build_t26_assets.py --phase v04-t26-assets
python Scripts/cpp_migration.py editor --script verify_t26_assets.py --phase v04-t26-reload
python Scripts/report_t26_config.py
python Scripts/run_t26.py
$fixed = (Get-Content Saved/V04/T26/latest_editor_logic_1280x720.json -Raw | ConvertFrom-Json).report
python Scripts/run_t26.py --render --compare $fixed
python Scripts/run_t26.py --render --width 1920 --height 1080 --compare $fixed
python Scripts/run_v03.py --from-menu
python Scripts/run_t18.py editor stats
python Scripts/run_t18.py editor decision
python Scripts/run_t18.py editor flow
python Scripts/package_v04.py
$exe = (Get-Content Saved/V04/T26/package_report.json -Raw | ConvertFrom-Json).exe
python Scripts/run_t26.py --exe $exe --render --compare $fixed
python Scripts/run_t26.py --exe $exe --render --width 1920 --height 1080 --compare $fixed
python Scripts/run_v03.py --exe $exe --from-menu --render
python Scripts/run_v03.py --exe $exe --from-menu --render --width 1920 --height 1080 --mute
python Scripts/run_t18.py packaged stats --map /Game/Prototype/Maps/L_LegacyPrototype --exe $exe
python Scripts/run_t18.py packaged decision --map /Game/Prototype/Maps/L_LegacyPrototype --exe $exe
python Scripts/run_t18.py packaged flow --map /Game/Prototype/Maps/L_LegacyPrototype --exe $exe
python Scripts/audit_t26_delivery.py --runtime <本轮通过的V03实景运行目录/runtime.log>
python Scripts/finalize_t26_evidence.py
python Scripts/checkpoint_v04.py --label T26_verified
```

生成器幂等，修改资产前另存 AssetsBefore_*；独立重载脚本不保存。勿运行旧全量 HUD/关卡生成器覆盖 T26；勿调用旧归档 verify（会改派生报告）。配置表脚本重建 Markdown 后需要重新追加测试结果。

正常试玩双击新包 AnomalyLab.exe，不加测试参数；需要完整 Windows 目录。当前无扫描充能/商店/长期经济/新怪物。Q/装备/四格背包/手动入口撤离保持旧玩法；左上区域提示说明倾向、不保证每箱安全。

恢复：Saved/V04/checkpoint_initialization.json 或 checkpoint_T26_verified.json 定位完整 Project 快照，将 Project 复制到新目录，核对 manifest 后按 ASCII 流程重建。不要覆盖旧快照后留住后来新增的 C++/uasset。v0.3 完整原版工程/包仍在 Saved/Releases/v0.3_ScenePolish_Accepted_20261011/，清单文件只读。
