# v0.4 incremental reproduction

Run from this project root in PowerShell; UE jobs use the existing background runner, without MCP or screen control.

```powershell
python Scripts/cpp_migration.py build-editor
python Scripts/run_v04.py --stage T27
python Scripts/run_v04.py --stage T28 --render
python Scripts/run_t29.py
python Scripts/run_v04.py --stage T29 --render --width 1920 --height 1080
python Scripts/run_v03.py --from-menu --render --mute
python Scripts/run_t26.py
python Scripts/run_t18.py editor flow --map /Game/Prototype/Maps/L_LegacyPrototype
```

Each run creates a timestamped evidence directory; assert status/logs and actual screenshots, not exit 0 alone. Save tests use unique Automation_* slots and remove only their own slot family even on failure. The dedicated cold-start suite retains its isolated slot between paired processes, then cleans it. Never pass a player slot to an automated driver.

Normal gameplay: menu → Level01 → ↑/↓ select, Enter purchase, E start → Q hold scan, 1 scanner/2 gun, E box or item → 1 continue / 2 return → physical entrance E settle → R new preparation. F drops a purchased decoy in a run. Default permanent money is 0. Batteries/precision/backpack are permanent; decoy is consumed at new-run entry and never duplicated by restart.

Normal SaveGame is AnomalyLab_Meta_v04.sav under the runtime ProjectSavedDir/SaveGames (read [MetaSave] Path in log). Keep .bak with the main file. Future schemas are preserved and commits blocked. Source checkpoints intentionally do not copy player SaveGames; restore Project into a new directory and rebuild rather than overlay old/new files.

T30–T32 commands and release identity will be added when those stages are implemented and verified. Human acceptance remains distinct from automated input and real rendering.

### T30 观察者
`python Scripts/run_t30.py --render`（另加 `--width 1920 --height 1080` 验证1080p）；`--exe <Windows/AnomalyLab.exe>` 切独立包。真实 E/R 队列、自然固定种子威胁、相机/位移夹具和实际渲染；不是真人试玩。输出 Saved/V04/T30/Runs，包含预警/正视/墙体/红眼/收容/死亡竞态六图。自动测试独立槽运行后清理。

### T31 / T32 RC
- `python Scripts/run_t31.py`：48格×5000局配置仿真；`--compare <Editor report.json>`核对全序列摘要/离散指标，派生浮点容限1e-12。死亡参数是假设，不是玩家测量。
- `python Scripts/package_v04_rc.py`：新建完整Win64 Development候选，不覆盖旧版本。
- `python Scripts/verify_v04_rc.py --exe <本工作区RC/Windows/AnomalyLab.exe>`：十五组包矩阵；各runner隔离槽。Development运行时Saved可能在Windows/AnomalyLab/Saved；清理仅自动测试确切槽族。
- `python Scripts/cold_boot_v04.py --exe <EXE>`：无自动驱动启动默认菜单；UE内建seconds=12自动退出，检查默认档字节未变。
- `python Scripts/restore_v04_candidate.py --package <RC根目录>`：复制全工程/完整包到NEW目录、逐文件SHA、启动恢复包菜单与资源/装备检查。
- `python Scripts/audit_v04_delivery.py`：只读基线差异及打包源对齐。
- `python Scripts/archive_v04_rc.py --package <RC根目录> --matrix <通过矩阵目录>`：一次性新归档；`--verify <归档>`只读校验，结果写当前Saved/V04/T32。v0.3旧归档验证也用此只读模式，不再用旧写回报告的verify脚本。
- 手动操作与记录：Docs/v0.4/PLAYTEST_RECORD.md；当前没有完成的真人样本。玩家存档不包含在版本恢复包中，个人保存应另行备份。
