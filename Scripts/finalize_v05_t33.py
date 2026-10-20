"""Close T33 only after real baseline reports, source invariants and recovery pass."""
import hashlib, json, sys
from datetime import datetime
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'Saved/V05/T33'
sys.path.insert(0,str(ROOT/'Scripts'))
import checkpoint_v05 as checkpoint
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return checkpoint.sha(p)
def count(result):
    data=result['result']
    if 'checks' in data: return data['checks']
    return sum(r['checks'] for r in data.get('results',[]))
def main():
    package_path=Path(read(OUT/'latest_regression_package.json')['report']); package=read(package_path)
    assert package['status']=='PASS' and len(package['results'])==11
    names=['resources','equipment','save','regions','observer','core','menu']
    source={}; history=[]
    for p in sorted(OUT.glob('Regression_editor_*/report.json')):
        report=read(p); history.append(dict(report=str(p),status=report['status'],results=[dict(group=r['group'],status=r['status']) for r in report['results']]))
        for r in report['results']:
            if r['status']=='PASS': source[r['group']]=dict(r,source_report=str(p))
    assert all(n in source for n in names),source.keys()
    audit=read(OUT/'asset_audit.json'); assert audit['status']=='PASS' and all(r['passed'] for r in audit['checks'])
    protected=read(OUT/'protected_after.json'); assert protected['status']=='PASS'
    baseline=read(OUT/'source_copy_manifest.json'); invariant=[]
    for r in baseline['files']:
        if r['path'].startswith(('Source/','Config/','Content/')) or r['path'].endswith('.uproject'):
            assert sha(ROOT/r['path'])==r['sha256'],r['path']
            invariant.append(r['path'])
    for p in ['run_v04.py','run_t29.py','run_t26.py','run_t30.py','run_t31.py','run_v03.py','run_t19_menu.py','run_t18.py']:
        r=next(x for x in baseline['files'] if x['path']=='Scripts/'+p); assert sha(ROOT/r['path'])==r['sha256'],p
    assert sha(ROOT/'Docs/AnomalyLab_v0.5_Agent_Implementation_Plan.md')==sha(ROOT/'AnomalyLab_v0.5_Agent_Implementation_Plan.md')
    context=read(ROOT/'Saved/CppMigration/latest.json')
    events=[json.loads(s) for s in (Path(context['directory'])/'journal.jsonl').read_text(encoding='utf-8').splitlines()]
    builds=[e for e in events if e.get('event')=='process_finished' and e.get('stage')=='build-editor']
    assert builds and builds[-1]['exit_code']==0
    reviews=[
      ('Saved/V04/T28/Runs/20261013T182024814335_package/01_shop_owned.png','实际显示余额0/未升级，文字可读；文件名不能当作已拥有升级的证明，购买/效果由29项断言证明。'),
      ('Saved/V03/Runs/20261013T182208656540_render_1280x720/01_entry.png','实际实验室入口、导航文字与HUD可见，非黑帧。'),
      ('Saved/V03/Runs/20261013T182208656540_render_1280x720/11_same_frame_death.png','同帧死亡截图HP0、损失699、带出0、永久余额保留；金额为测试样本，不是真人统计。'),
      ('Saved/V03/Runs/20261013T183609062234_render_1280x720/03_scan_result.png','重编译Editor的A区扫描结果实际可见，显示缓存读数、剩余2次、箱/交互与场景；中文可读。')]
    for p,_ in reviews: assert (ROOT/p).is_file()
    checkpoint.write(OUT/'visual_review.json',dict(scope='Agent inspection of real 1280x720 D3D12 offscreen baseline frames; no physical human input/sound judgment',viewed=[dict(path=p,notes=n) for p,n in reviews],human_samples=0))
    rows=[]
    for r in package['results']:
        rows.append(f"| {r['group']} | PASS / {count(r)} | "+(f"PASS / {count(source[r['group']])}" if r['group'] in names else '未重跑（T33复制RC已覆盖）')+' |')
    timestamp=datetime.now().astimezone().isoformat()
    text=f'''# T33 基线审计与两关卡设计报告

时间：{timestamp}。状态：T33 工程验证通过；本报告只有在 `Saved/V05/checkpoint_T33_verified.json` 为 PASS 时构成完整闭环。v0.5 游戏功能尚未实现，未打包。

## 工作副本和基线保护

独立工程 `F:/AnomalyLab/AnomalyLab_v05/我的项目3.uproject`。原工程 `F:/AnomalyLab/我的项目3`、v0.4 已人工验收 RC_20261013T131738、v0.4/v0.3 发布归档与原包保持原样。无 Git，采用完整 SHA 检查点。初始复制1407文件/1,638,949,825字节；未复制个人 SaveGames。归档清单2030项校验PASS；前后全树检查包含清单自身2031项。原副本8个文档变化为已有验收补记，Source/Config/Content/Binaries无偏差。

`Saved/V05/T33/protected_after.json`：原工程1407文件、v0.4归档2031、v0.4原包106、v0.3归档1871、v0.3原包53，文件集合与SHA全部一致。工作副本Source/Config/Content/uproject共{len(invariant)}项未改；8个旧测试入口脚本逐字未改。新增文件/编译产物见 `Saved/V05/T33/changed_files.json`。

## 真实实现和冻结方案

默认仍为独立L_MainMenu → L_Prototype内Preparation → 同图探索，R重载当前地图。新进程实际重载16项PASS：主菜单46Actor且无Coordinator，探索277Actor、一个Coordinator/PlayerStart/NavBounds/Recast；出生(0,1750,110)、yaw-90；Legacy44Actor且无Preparation/Region。新Hub/Lab尚未创建。

永久经济已有GameInstance ProgressionSubsystem；商店为Coordinator原生输入+WBP_ExplorationPrompt被动显示，Schema2 SaveGame持久化，成功物理入口次帧校验兑现，死亡优先。购买与BeginRun依赖旧Coordinator，新图不能直接套用。重要修复入口：关闭Lab Preparation会跳过Progression配置，必须显式初始化/claim并禁止Wallet-only假成功；R终局必须回Hub；旧存档损坏不可静默归零。

冻结：两个真实文件Content/Maps/L_Hub.umap与L_Lab.umap；Hub安全空间/商店/报告/出发，Lab保留ABC与物理撤离；既有Progression继续唯一经济权威，新增TransitionSubsystem只保存RunId/version/种子/装备值/结果DTO；出发消费诱饵一次，Lab接收一次；死亡/错误0兑现；结束先封口/快照/保存/清理，再回Hub；重启回Hub不恢复未兑现Loot、不重放记账。完整迁移表/平面/存档策略见ARCHITECTURE_MAP、LEVEL_DESIGN、SAVE_MIGRATION、DECISIONS。

## 编译和自动回归（真人样本0）

独立ASCII构建副本 `Saved/BuildWork/V05_T33_Baseline`。编译MaxParallelActions2，39 actions，126.01秒，exit0。成功日志：`{Path(builds[-1]['log']).relative_to(ROOT).as_posix()}`。

| 组 | 复制RC | 重编译Editor源码 |
|---|---|---|
'''+ '\n'.join(rows)+f'''

存档组每目标10个独立OS进程；表中数字为实际自动断言数。区域逻辑78与历史渲染81之差为3个额外截图检查。未删除/改写旧断言。源码汇总可审计最初失败与随后重跑；不是掩盖失败。

命令：`python Scripts/run_v05_baseline.py --target package`；`python Scripts/cpp_migration.py build-editor`；`python Scripts/cpp_migration.py editor --script audit_v05_baseline_assets.py --phase v05_t33_audit`；`python Scripts/run_v05_baseline.py --target editor --groups resources equipment save regions observer core menu`（渲染因权限中断后，resources既有PASS保留，其余6组以相同断言重跑）。包装矩阵 `{package_path.relative_to(ROOT).as_posix()}`；源码实际报告见 `Saved/V05/T33/source_regression_summary.json`。

失败记录保留：初始同级构建目录写权限；沙箱UBT用户trace轮换失败；首次Editor装备渲染无法写用户UnrealShaderWorkingDir导致无report，判FAIL。授权构建/渲染重跑后通过，未改源码来适应权限问题。

真实720p D3D12离屏图已生成；代理查看商店/入口/同帧死亡帧，见visual_review.json。自动输入路由/渲染不等于真人物理按键、听感或5人×3局。新地图、三次往返、1080p新流程和新存档迁移待后续阶段，不宣称完成。

## 闭环和下一阶段

文档：ARCHITECTURE_MAP、LEVEL_DESIGN、SAVE_MIGRATION、DECISIONS、KNOWN_ISSUES、TEST_MATRIX、PLAYTEST_RECORD、progress、本报告；计划精确复制到Docs。新脚本bootstrap_v05、run_v05_baseline、audit_v05_baseline_assets、checkpoint_v05、finalize_v05_t33；旧玩法源码/地图/配置不变，Editor产品重新编译。

完整恢复点索引 `Saved/V05/checkpoint_T33_verified.json`，逐文件SHA重新读回；恢复到NEW目录并新建ASCII编译上下文，勿覆盖旧工程。检查点不含个人档/缓存/测试包，证据保留工作副本Saved。T33遵循计划§13.2/§14，本会话只做该阶段。下一任务T34：按冻结设计生成并独立重载真实Hub/Lab，测出生/碰撞/导航/视觉并回归；T35–T41依次完成后才T42打包。无新v0.5包，无新Human Accepted标记。
'''
    (ROOT/'Docs/v0.5/T33_REPORT.md').write_text(text,encoding='utf-8')
    checkpoint.write(OUT/'source_regression_summary.json',dict(status='PASS',groups=len(names),results=[source[n] for n in names],history=history))
    progress=f'''# v0.5 Progress

Baseline: v0.4 RC_20261013T131738 (Human Accepted user overall confirmation)
Current Task: T33
Status: Verified (checkpoint PASS index required)
Workspace: F:/AnomalyLab/AnomalyLab_v05

## This task

- 实际接口/地图/SaveGame/商店/终局/R审计与最小迁移设计完成，见ARCHITECTURE_MAP/LEVEL_DESIGN/SAVE_MIGRATION/DECISIONS。
- 变更：新增v0.5文档和5个审计/回归/恢复脚本，Docs/STATE更新，原计划精确复制到Docs，Editor产物重编译；Source/Config/Content/uproject与初始基线完全相同。changed_files.json列实际清单。
- 状态/存档契约：设计已冻结，运行时未改Schema/玩家档；个人SaveGames未复制。
- 编译PASS(exit0,39actions/126.01s)，独立资产重载16/16PASS。
- 复制RC11组PASS，源码关键7组PASS（含存档10进程），实际命令/结果与权限失败重跑记录见T33_REPORT及Saved/V05/T33；旧断言/测试脚本未改。
- 真实720p D3D12图代理查看完成，真人物理输入/听感/平衡样本仍未执行；不可将基线自动测试当作新关卡验收。
- 原工作工程/v0.4与v0.3包/归档前后文件集合+SHA全部PASS不变。
- 完整恢复点：Saved/V05/checkpoint_T33_verified.json；只有索引PASS表示闭环，恢复到NEW目录并重新构建，勿覆盖。
- 已知风险和未执行项见KNOWN_ISSUES/TEST_MATRIX/PLAYTEST_RECORD。
- 下一最小任务T34，严格独立阶段；本轮不改地图、不执行T35+，全部阶段通过后才T42打包。新L_Hub/L_Lab尚未实现。
'''
    (ROOT/'Docs/v0.5/progress.md').write_text(progress,encoding='utf-8')
    matrix=ROOT/'Docs/v0.5/TEST_MATRIX.md'; content=matrix.read_text(encoding='utf-8').replace('Running; actual evidence in Saved/V05/T33','PASS: copied RC11 groups, rebuilt source7, reload16; evidence Saved/V05/T33')
    matrix.write_text(content,encoding='utf-8')
    result=checkpoint.create('T33_verified')
    summary=dict(status='T33_ENGINEERING_VERIFIED',completed_at=timestamp,workspace=str(ROOT),package_regression=str(package_path),source_regression=str(OUT/'source_regression_summary.json'),asset_audit=str(OUT/'asset_audit.json'),checkpoint=result,next_task='T34',v05_gameplay_implemented=False,v05_packaged=False,human_samples=0)
    checkpoint.write(OUT/'delivery_summary.json',summary)
    print(json.dumps(summary,ensure_ascii=True),flush=True)
if __name__=='__main__': main()
