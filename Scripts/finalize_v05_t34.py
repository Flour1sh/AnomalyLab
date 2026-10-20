"""Close T34 only after current-module runtime, regression and protection gates."""
import json
from datetime import datetime
from pathlib import Path
from checkpoint_v05 import ROOT, OUT, sha, write, create


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    task = OUT / 'T34'
    # Preserve the interrupted full matrix as FAIL. Reuse its successful new-map
    # evidence and require an independently completed, full regression report.
    matrix_path = task / 'Matrix_20261013T200231/report.json'
    matrix = read(matrix_path)
    gates = {r['name']: r for r in matrix['results']}
    names = ['build', 'reload', 'Hub_720', 'Lab_720', 'Menu_720',
             'Hub_1080', 'Lab_1080', 'Menu_1080']
    assert all(gates[n]['status'] == 'PASS' and gates[n]['exit_code'] == 0 for n in names)
    build = read(read(task / 'latest_build.json')['report'])
    assert build['status'] == 'PASS' and build['layout_version'] == 2
    reload = gates['reload']['result']
    assert reload['status'] == 'PASS' and len(reload['checks']) == 31
    assert all(c['passed'] for c in reload['checks'])
    module = sha(ROOT / 'Binaries/Win64/UnrealEditor-AnomalyLab.dll')
    frames = []
    runtime = []
    for name in names[2:]:
        result = gates[name]['result']
        assert result['module_sha256'] == module and result['human_samples'] == 0
        folder = Path(result['directory'])
        detail = read(folder / 'report.json')
        assert detail['status'] == 'PASS' and all(c['passed'] for c in detail['checks'])
        screenshots = sorted(folder.glob('*.png'))
        assert len(screenshots) == result['frames']
        frames.extend(dict(path=str(p), sha256=sha(p)) for p in screenshots)
        runtime.append(dict(name=name, **result))
    assert len(frames) == 24
    visual = read(task / 'visual_review.json')
    assert visual['status'] == 'PASS' and visual['human_samples'] == 0
    assert {r['path']: r['sha256'] for r in visual['frames']} == {r['path']: r['sha256'] for r in frames}
    regression_path = Path(read(task / 'latest_regression_editor.json')['report'])
    regression = read(regression_path)
    expected = {'resources', 'equipment', 'save', 'regions', 'observer', 'balance',
                'core', 'menu', 'legacy_stats', 'legacy_decision', 'legacy_flow'}
    assert regression['status'] == 'PASS'
    assert {r['group'] for r in regression['results']} == expected
    assert all(r['status'] == 'PASS' and r['exit_code'] == 0 for r in regression['results'])
    for group in regression['results']:
        result = group['result']
        leaves = result['results'] if group['group'] == 'save' else [result]
        for leaf in leaves:
            assert leaf['status'] == 'PASS'
            raw_path = leaf.get('report') or str(Path(leaf['directory']) / 'runtime_report.json')
            raw = read(raw_path)
            assert raw['status'] == 'PASS' and all(c['passed'] for c in raw['checks'])
    protection = read(task / 'protected_after.json')
    assert protection['status'] == 'PASS' and all(r['status'] == 'PASS' and not r['changed'] for r in protection['results'])
    manifest = read(OUT / 'T33/source_copy_manifest.json')
    old_content = [r for r in manifest['files'] if r['path'].startswith('Content/')]
    assert len(old_content) == 1081
    assert all((ROOT / r['path']).is_file() and sha(ROOT / r['path']) == r['sha256'] for r in old_content)
    old_names = {r['path'] for r in old_content}
    added_content = [p.relative_to(ROOT).as_posix() for p in (ROOT / 'Content').rglob('*')
                     if p.is_file() and p.relative_to(ROOT).as_posix() not in old_names]
    assert all(p in ('Content/Maps/L_Hub.umap', 'Content/Maps/L_Lab.umap')
               or p.startswith('Content/Prototype/V05/') for p in added_content), added_content
    assert not (ROOT / 'Builds/v0.5').exists(), 'T34 must not package'
    summary = dict(status='PASS', task='T34', module_sha256=module,
                   source_matrix=str(matrix_path), map_gates=[gates[n] for n in names],
                   regression_report=str(regression_path), runtime_checks=138,
                   rendered_frames=24, protected_content=1081, visual_review=str(task / 'visual_review.json'),
                   protection_report=str(task / 'protected_after.json'), human_samples=0,
                   packaged=False, scope='T34 map/safety scaffold only; T35/T36 transactions pending')
    write(task / 'verification_summary.json', summary)
    now = datetime.now().astimezone().isoformat()
    rows = []
    for result in regression['results']:
        count = (sum(r['checks'] for r in result['result']['results'])
                 if result['group'] == 'save' else result['result'].get('checks'))
        rows.append(f"| {result['group']} | PASS | {count} |")
    report = f'''# T34 两关卡地图与安全基地报告

更新：{now}。状态：**T34 地图与安全框架工程验证通过**；完整恢复闭环以 `Saved/V05/checkpoint_T34_verified.json` 为 PASS 为准。工作副本 `F:/AnomalyLab/AnomalyLab_v05`，UE5.8。v0.5 购买与正式 Hub↔Lab 游戏闭环仍待 T35/T36；没有打包或宣称人工验收。

## 交付与模块边界

真实独立地图 `Content/Maps/L_Hub.umap`（51 Actor，导航8 tile）和 `L_Lab.umap`（278 Actor，导航28 tile）。Hub约16×20米，独立安全 Character、PlayerController、GameMode、被动UMG与4种终端；无扫描/装备/HP/钱包组件，无 Coordinator/危险箱/追逐者/观察者，伤害为0。WASD/鼠标/跳跃已接入；实际W轴移动、300cm与遮挡判定、E查看/ESC恢复输入由自动测试验证，鼠标观察/跳跃的真人物理输入仍待验收。商店目录和整备概览读取既有 Progression/Config，只读；出发通道明确未开放，战报为空状态，不伪造购买或结果。

默认菜单开始按钮进入 Hub，保留原加载防连点与输入恢复。新菜单为独立WBP_MainMenu_V05副本，旧蓝图不变。旧菜单/核心断言仅通过显式Development参数 `-AnomalyLegacyMenuRoute` 验证兼容路由；新正常路由测试没有该参数。

Lab从已保存L_Prototype可追溯复制，保留ABC场景、原角色/HUD、扫描/装备和数据引用。出生点(0,1750,110)，yaw=-90，入口标为撤离气闸。新增 `bAwaitLevelLaunch` 默认false，只有新Lab为true：独立打开可勘察，但没有授权RunId，不生成箱、不消费诱饵、不购物、不兑现。此门控防止T35未接入时绕过经济初始化。旧图行为由11组回归确认。T35需以真实launch claim/DTO替换等待分支，接入冻结装备、返回结算及死亡回Hub；T36接入实际商店操作与报告。

新增源码模块为 `AnomalyHub.h/.cpp`、`AnomalyV05LevelSmoke.cpp`；现有Coordinator只增加默认关闭的门控，菜单路由单独改动，Progression只增加自动测试存档白名单，SaveGame Schema2不变。场景布局与UE构建分为 `t34_layout.py`、`build_v05_levels.py`；生成器仅写新图/Prototype/V05资产，版本2重复执行幂等。原1081个Content文件SHA全部不变。

## 验证与证据

最终C++编译PASS：`Saved/CppMigration/V05_T34_20261013T190745/build-editor_20261013T120027559644Z.log`。DLL SHA256：`{module}`。新图测试六个独立进程均使用这一DLL。

| 新地图检查 | 结果 |
|---|---|
| 版本2第二次生成幂等、新进程实际资产重载 | PASS / 31断言 |
| Hub 1280×720、1920×1080 | 各PASS / 43断言、5帧 |
| Lab 1280×720、1920×1080 | 各PASS / 20断言、5帧 |
| 正常菜单→Hub 两分辨率 | 各PASS / 6断言、2帧 |

运行断言共138，实际D3D12离屏截图24；代理逐帧查看了Hub全景/商店/整备/出发/战报空态、Lab入口/ABC/出口和菜单前后。中文未裁切，无黑屏/空Pawn/出生重叠；气闸标识重叠与等待HUD空背景已修正。图片、SHA及具体观察见 `Saved/V05/T34/visual_review.json`。这些是自动输入和代理截图复核；真人样本0，不等同真人键鼠或听感验收。

运行测试包括真实W轴移动、胶囊撞墙后停止、终端距离/临时阻挡拒绝、重复E、ESC恢复、Hub无危险输入/伤害/财务变化；Lab保存完整Nav路径到ABC/入口并验证拒绝未经授权的开局/购物/结算；菜单由实际StartButton委托进入Hub并卸载旧Widget。视角定位使用明确的测试夹具，未作为连续物理行走或正式往返证明。

旧版当前源码完整回归：`{regression_path.relative_to(ROOT).as_posix()}`。

| 组 | 结果 | 自动断言 |
|---|---|---|
''' + '\n'.join(rows) + '''

存档组含10个独立OS进程，26项检查；使用Automation_隔离槽并清理，未复制或操作个人存档。原断言保留，区域/平衡引用只读历史报告。

## 保留的失败与恢复

初始编译私有伤害字段/成员名冲突及生成器Python属性访问失败已修复并重跑。首次Hub墙阈值与实测1000cm墙面/34cm胶囊不符，改为实测边界和停止速度；E/ESC与CameraCache同帧断言改为经过真实输入帧后验证，增加实际遮挡拒绝，未强制成功。失败报告和日志均保留。

`Matrix_20261013T200231/report.json` 中生成/重载/六个新图测试PASS，但首次资源回归子进程exit1且runner.log为空，因此整份旧矩阵仍保留FAIL；不能确定终止原因，不能当作玩法失败或成功。恢复断点后独立重跑全部11组PASS。权威合并证据是 `Saved/V05/T34/verification_summary.json`，没有改写旧矩阵状态。

旧GameFeatures.GameFeatureData handled ensure在T33日志已存在，保留原配置并记录，不隐去。正式购买、三次Hub↔Lab、撤离/死亡/错误优先、重启恢复、旧档迁移、跨场景AI/音频清理及独立包检查仍待后续对应阶段。

## 基线保护、恢复与下一阶段

`Saved/V05/T34/protected_after.json` 全集合/SHA检查PASS：原工程1407文件、v0.4归档2031、v0.4已验收原包106、v0.3归档1871、v0.3原包53，均无新增/删除/改动。T33恢复点保持原样。T34新增/修改/删除清单见 `Saved/V05/T34/changed_files.json`；恢复点索引为 `Saved/V05/checkpoint_T34_verified.json`，包含源码/配置/Content/脚本/文档/Editor二进制/模型音频原文件并逐文件SHA复读验证。恢复必须到新目录，不覆盖原工程；同盘检查点不防磁盘损失。

复现命令：

```powershell
python Scripts/cpp_migration.py build-editor
python Scripts/verify_t34_matrix.py --regression
python Scripts/checkpoint_v05.py --task T34 --audit-protected
python Scripts/finalize_v05_t34.py
```

本次恢复复用未变DLL及新图已通过的结果，单独执行 `python Scripts/run_v05_baseline.py --target editor --task T34` 补全回归。finalize只校验已有证据、写报告并创建SHA恢复点，不替代编译/测试；必须先有代理截图复核记录。

下一任务为T35：跨Level路由、RunId/出发消费与claim、结算幂等、死亡返回、重启/异常恢复和旧档兼容。本轮不启动T35。所有阶段完成后才进行T42打包；独立包、返回战报真实结果截图和人工验收仍待完成。
'''
    (ROOT / 'Docs/v0.5/T34_REPORT.md').write_text(report, encoding='utf-8')
    (ROOT / 'Docs/v0.5/progress.md').write_text('''# v0.5 Progress

Baseline: v0.4 RC_20261013T131738
Current Task: T34
Status: Verified (map/safety scaffold; checkpoint index must be PASS)
Workspace: F:/AnomalyLab/AnomalyLab_v05

- 独立L_Hub/L_Lab已生成，51/278 Actor、导航8/28 tile；菜单正常启动进入Hub。
- Hub使用独立安全Pawn/Controller/GameMode/UI，4终端只读；Lab等待真实launch授权，禁止未经授权开局/购买/结算。SaveGame Schema2和经济权威不变。
- C++最终编译PASS，版本2生成幂等及独立资产重载31断言PASS；720/1080六个D3D12进程138断言、24实际帧，代理逐帧复核完成；真人物理输入/音效/试玩未做。
- 当前源码旧11组回归全PASS，存档10进程/26项；显式Legacy菜单测试与正常生产路由分别验证，原断言未弱化。
- 原1081个Content SHA不变；原工程/已验收RC/v0.3与v0.4归档全集合SHA不变。T33检查点不覆盖。
- 所有命令、失败与补跑、证据路径见T34_REPORT.md及Saved/V05/T34/verification_summary.json；变更清单changed_files.json，完整恢复点Saved/V05/checkpoint_T34_verified.json。
- 下一最小任务T35：跨关卡路由、RunId和一次结算、死亡返回及恢复。购买/出发闭环和实际返回战报待T35/T36；独立包按要求延后T42。未打包。
''', encoding='utf-8')
    (ROOT / 'Docs/STATE.md').write_text('''# CURRENT IMPLEMENTATION STATE

更新：2026-10-14 / Asia/Shanghai。独立v0.5工作副本，当前T34地图与安全框架工程验证通过，完整恢复闭环以Saved/V05/checkpoint_T34_verified.json的PASS为准。

- 工程F:/AnomalyLab/AnomalyLab_v05/我的项目3.uproject，UE5.8，无Git，完整SHA检查点。
- 不可修改基线为原工程及已人工总体验收v0.4 RC_20261013T131738；v0.3/v0.4原包及归档SHA无变化。
- 默认L_MainMenu→L_Hub；两个真实文件Content/Maps/L_Hub.umap、L_Lab.umap，旧L_Prototype/Legacy/菜单资产1081项字节不变。
- Hub独立安全角色/UI/4终端，仅查看既有Meta配置；无伤害、扫描、箱和怪物。Lab保留ABC/原角色/HUD/数据，并以bAwaitLevelLaunch拒绝未经授权开局/消费/购买/结算。
- 永久经济继续由UAnomalyProgressionSubsystem及Schema2 SaveGame唯一管理；没有第二份账户系统，个人SaveGames未复制/操作。
- T34编译、生成幂等、新进程重载31断言、新场景六个D3D12测试138断言/24帧、当前源码旧11组回归及基线SHA全部PASS。断点中止矩阵的FAIL原样保留，补跑与汇总见Docs/v0.5/T34_REPORT.md。
- 源码/脚本/配置职责与扩展边界见v0.5/ARCHITECTURE_MAP.md、DECISIONS.md、LEVEL_DESIGN.md、T34_PLAN.md。最终证据为Saved/V05/T34/verification_summary.json。
- T33恢复点保留；T34完整快照与变更清单见checkpoint_T34_verified.json及T34/changed_files.json。恢复到新目录，不覆盖基线，重新建立ASCII构建上下文。
- 当前不是完整v0.5可玩闭环。T35负责真实出发claim、跨图结算/死亡/错误与重启恢复；T36负责Hub购买/整备/实际战报。三次往返、旧档迁移、动态机制/事件、性能和T42独立包仍待对应阶段。
- 全部阶段通过后才打包。代理截图检查与真人验收分开；真人样本0，PLAYTEST_RECORD未执行，不宣称Human Accepted。
''', encoding='utf-8')
    matrix_doc = ROOT / 'Docs/v0.5/TEST_MATRIX.md'
    value = matrix_doc.read_text(encoding='utf-8')
    lines = value.splitlines()
    for i, line in enumerate(lines):
        if line.startswith('| T34 |'):
            lines[i] = '| T34 | real two .umap fresh reload, mode/input/Pawn/nav/collision, safety, idempotent builder, SHA, 720/1080 | PASS: reload31; runtime138 in6 processes/24 frames; current-source regression11; proxy visual review; summary Saved/V05/T34/verification_summary.json. T35/T36 transactions and T42 package pending |'
    matrix_doc.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    issues = ROOT / 'Docs/v0.5/KNOWN_ISSUES.md'
    value = issues.read_text(encoding='utf-8').replace(
        '- T33 only: Hub/Lab maps and travel/gameplay not implemented yet; v0.5 not playable or packaged. Do not describe baseline regression as new-feature acceptance.',
        '- Current T34: real Hub/Lab maps verified; formal travel/transactions remain T35/T36. v0.5 full gameplay is not complete or packaged. T33 reports remain historical evidence.')
    marker = '## T34 final recovery result'
    if marker not in value:
        value += '''\n## T34 final recovery result

- E/ESC输入与相机缓存需跨真实帧验证；测试时序已修正，距离/遮挡/重复操作仍严格拒绝，原FAIL保留。
- 最终气闸文字重叠与空RegionBacking已修正；两分辨率24实际帧均由代理查看，真人样本0。
- 20261013T200231矩阵新图全部PASS，资源回归exit1且空runner.log导致总FAIL，原因不确定。恢复后完整11组独立回归PASS，旧FAIL不改写，verification_summary.json串联真实结果。
- 等待授权Lab仍显示原扫描提示，但无合法Run/箱或消费；完整局内HUD与实际返回战报由T35/T36接入验证。截图不代表游戏往返已完成。
'''
    issues.write_text(value, encoding='utf-8')
    checkpoint = create('T34_verified', 'T34')
    write(task / 'delivery_summary.json', dict(status='PASS', task='T34', checkpoint=checkpoint,
          verification=str(task / 'verification_summary.json'), report=str(ROOT / 'Docs/v0.5/T34_REPORT.md'),
          packaged=False, human_samples=0))
    print(json.dumps(dict(status='PASS', checkpoint=checkpoint, report=str(ROOT / 'Docs/v0.5/T34_REPORT.md')), ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
