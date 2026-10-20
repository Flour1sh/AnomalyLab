"""Finalize reviewable engineering delivery only after package, restore and agent frame review."""
import json
from pathlib import Path
from datetime import datetime
from checkpoint_v05 import ROOT,write,sha,create,protected
def main():
    base=ROOT/'Saved/V05/T42';pkg=json.loads((base/'package_report.json').read_text(encoding='utf-8'))
    index=json.loads((base/'latest_matrix.json').read_text(encoding='utf-8'));matrix=json.loads(Path(index['report']).read_text(encoding='utf-8'))
    restore=json.loads((base/'restore_report.json').read_text(encoding='utf-8'));visual=json.loads((base/'visual_review.json').read_text(encoding='utf-8'))
    clean=json.loads((base/'clean_package.json').read_text(encoding='utf-8'))
    assert pkg['status']==matrix['status']==restore['status']==visual['status']==clean['status']=='PASS'
    assert Path(matrix['exe']).resolve()==Path(pkg['exe']).resolve() and visual['human_samples']==0
    assert all(sha(ROOT/name)==digest for name,digest in json.loads(Path(pkg['source_manifest']).read_text(encoding='utf-8')).items())
    audit=protected('T42');release=Path(pkg['directory']).name;archive=ROOT/'Saved/Releases'/('v0.5_'+release+'_HumanPending')
    docs=ROOT/'Docs/v0.5';now=datetime.now().astimezone().isoformat()
    text=f'''# AnomalyLab v0.5 交付报告

Engineering Verified / Awaiting Human Validation。{now}。真人样本0，未标记HumanAccepted。

完整 Win64 Development 包（与测试候选全量SHA一致的新目录，不带自动化设置/存档）：{Path(clean['exe']).as_posix()}。保持整个 Windows 目录，正常双击 AnomalyLab.exe；默认菜单进入独立安全基地 L_Hub，出发进入独立探索 L_Lab。

T35–T42分别执行实现、编译/适当自动化、新功能与相关旧回归、报告和SHA恢复点。T35跨场景结算/存档；T36共享购买权威；T37动态合法点位与独立RNG；T38配电；T39收容舱；T40两类有实际效果的环境事件；T41统计/加载反馈/步行流程；T42完整包验证与恢复归档。逐阶段报告及恢复索引见T35_REPORT.md至T42_REPORT.md、Saved/V05/checkpoint_Txx_verified.json。

T42首候选暴露A6旧掉落偏移被标本架遮挡。v0.5新增可配置掉落位置的球体/视线校验及有限站位回退，并在生成时复核；旧图偏移和奖励RNG不变。加强后的20局713断言逐局执行真实E拾取与实际价值结算；源预检及最终包完整矩阵均通过。首候选和失败日志保留。

额外边界回归覆盖：已携带物品时发生关卡技术错误，战报准确记录损失且不增加永久余额；独立Error分支与保存写入故障分别测试。第二候选的矩阵因补充这条源代码修复而明确标记INTERRUPTED，已有证据保留；最终候选完整重测。

包内矩阵：{index['report']}。共{len(matrix['results'])}个顺序任务，覆盖新玩法、20次地图往返、多点合法性、交易/异常/去重、跨进程重启、携带未兑现/已兑现尚未回Hub两种真实OS强制中断、正常启动旧档导入、720p/1080p实际D3D12画面、全部11组旧回归和Legacy。测试夹具、NullRHI与渲染模式均保留在原始命令/日志；自动输入和截图审阅不作为真人证据。

恢复验证：{(Path(restore['directory'])/'report.json').as_posix()}。全量源工程{restore['project_files']}文件及完整包{restore['package_files']}文件复制到新目录后SHA复读，通过恢复源Editor Hub启动与恢复包三次步行往返。未在恢复目录重新编译；源恢复重建需UE5.8和新的ASCII构建上下文。

代理画面审阅：Saved/V05/T42/visual_review.json。加载盖层、菜单/商店、扫描/背包、成功/死亡战报、配电/警报及两个分辨率的真实帧已单独记录。最终听感、真实键鼠、公平性、自然局长与平衡由用户统一人工测试，使用HUMAN_TEST_GUIDE.md/PLAYTEST_RECORD.md。

T41及包内性能原始数据见Saved/V05/T41/telemetry_audit.json与Saved/V05/T42/telemetry_audit.json。FPS为20Hz抽样的引擎CPU帧间隔，包含加载/截图开销；不是GPU基准，不声称60FPS或3–5分钟真人目标达标。统计限20文件，事件/样本/文件大小有上限，可用-NoRunTelemetry关闭，不参与经济权威。

版本兼容：保留Schema2及原槽名，Progression为唯一永久经济管理者。导入仅对无主档/备份的新目标生效，源文件只读。不可读现有档阻止购买/出发；崩溃/退出不兑现携带物品，出发后已消费诱饵不退款。测试只用Automation_隔离槽，未导入任何玩家真实档。

基线：1081旧Content、原工程非文档载荷、已验收v0.4 RC和v0.3/v0.4归档SHA保持。原工程4份文档在外部维护中变化，固定路径+SHA例外证据Saved/V05/T35/external_baseline_document_changes.json；初始严格身份FAIL保留，未重设清单。本任务没有写入原工程/RC/归档。

完整恢复归档：{archive.as_posix()}，含Project/、完整Package/Windows/、成功与失败Evidence/及release_manifest.json。最终归档SHA复读和T42恢复点状态以Saved/V05/T42/release_archive.json、delivery_summary.json、checkpoint_T42_verified.json为准。归档为同盘恢复副本。

已知边界与原失败保留见KNOWN_ISSUES.md；原有GameFeatures handled ensure未隐藏。任何人类验收结论需用户后续提供。
'''
    (docs/'FINAL_REPORT.md').write_text(text,encoding='utf-8')
    (docs/'T42_REPORT.md').write_text('# T42 工程阶段报告\n\n'+text.split('\n',1)[1]+f'\n构建日志：{pkg["log"]}\n源清单：{pkg["source_manifest"]}\n包清单：{pkg["payload_manifest"]}\n',encoding='utf-8')
    guide=(docs/'HUMAN_TEST_GUIDE.md').read_text(encoding='utf-8')
    guide=guide.replace('# v0.5 最终统一人工测试单（草稿，交付时补启动路径）','# v0.5 最终统一人工测试单')
    guide+='\n\n启动包：'+Path(clean['exe']).as_posix()+'\n\n完整复制同级Windows目录后启动根AnomalyLab.exe。首次新目录无旧档时余额0，先探索/拾取并物理撤离获得永久币，再购买。自动化10000币仅测试夹具，不是玩家初始资产。\n\n'
    guide+='基地：WASD/鼠标/空格；对准终端E，商店↑↓选择、ENTER购买、ESC关闭；出发E预览、ENTER确认。探索：按住Q扫描；1切换仪器、2装备枪；对准箱/物品/设备E。决策时1继续、2返回入口；必须回气闸E才兑现。F使用已带入诱饵。死亡自动回基地，R不能绕过结算重开Lab。\n\n'
    guide+='新包显式导入旧档：先备份旧sav/bak，只在新包目标无主档/备份时，用命令行运行AnomalyLab.exe -AnomalyImportSave="旧sav绝对路径"。确认基地显示余额/升级，旧文件保留。已有有效新档不覆盖；损坏档先备份并按SAVE_MIGRATION.md恢复，不直接删除。实际存档路径见AnomalyLab/Saved/Logs中的[MetaSave]。\n\n'
    guide+='B终端在B房内；关电扫描耗时×1.75，但B区正视观察者压制容忍×1.50。C绿圈内活动普通追逐者可封锁3秒，本局一次；观察者免疫。事件有预警，B可手动恢复；C警报短暂加速追逐者，可用舱/离开C区。建议每位参与者至少三次往返并填写PLAYTEST_RECORD.md，问题附结果截图/日志和复现步骤。\n'
    (docs/'HUMAN_TEST_GUIDE.md').write_text(guide,encoding='utf-8')
    state=f'# CURRENT IMPLEMENTATION STATE\n\n{now} / Asia/Shanghai。T35–T42工程实现及自动/回归门槛通过；Engineering Verified / Awaiting Human Validation，真人样本0。\n\n启动：{Path(clean["exe"]).as_posix()}。完整Windows包，不单独复制exe。最终交付索引Saved/V05/T42/delivery_summary.json及checkpoint_T42_verified.json；统一人工测试Docs/v0.5/HUMAN_TEST_GUIDE.md，详细证据Docs/v0.5/FINAL_REPORT.md。\n\n独立Hub/Lab、唯一Progression经济、购买/冻结装备/出发/撤离/死亡/存档/结算、动态点位/配电/舱/事件/有界统计均已接入。旧RC/归档/1081旧Content不变；外部4Docs变化按固定SHA单独记录，初始严格FAIL保留。\n'
    (ROOT/'Docs/STATE.md').write_text(state,encoding='utf-8')
    (docs/'progress.md').write_text(f'# v0.5 Progress\n\nCurrent Task: T42\nStatus: Engineering Verified / Awaiting Human Validation\n\n{state.split(chr(10),2)[2]}',encoding='utf-8')
    matrix_path=docs/'TEST_MATRIX.md';lines=matrix_path.read_text(encoding='utf-8').splitlines()
    for i,line in enumerate(lines):
        if line.startswith('| T42 |'):parts=line.split('|');parts[-2]=' PASS engineering: full package matrix, dual-resolution frames, source/package restore, SHA archive; final human validation pending ';lines[i]='|'.join(parts)
    matrix_path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    issue=docs/'KNOWN_ISSUES.md';value=issue.read_text(encoding='utf-8');value=value.replace('T35–T40 engineering gates passed. T41 adds diagnostics, loading cover and real synthetic walking; T42 package verification follows only after T41 passes.','T35–T42 engineering and packaged gates passed. Diagnostics, loading cover, synthetic walking, full package and new-directory recovery are verified.')
    value=value.replace('final candidate must pass the complete packaged matrix.','final candidate passed the complete packaged matrix; the first failure is historical evidence.')
    issue.write_text(value,encoding='utf-8')
    gate=dict(status='PASS',task='T42',package=pkg,clean_package=clean,matrix_report=index['report'],restore_report=str(base/'restore_report.json'),visual_report=str(base/'visual_review.json'),human_samples=0,acceptance='AWAITING_HUMAN_VALIDATION')
    write(base/'gate_report.json',gate);write(base/'latest_gate.json',dict(status='PASS',report=str(base/'gate_report.json')))
    checkpoint=create('T42_verified','T42');write(base/'finalization.json',dict(status='PASS',checkpoint=checkpoint,archive_expected=str(archive),human_samples=0));print(json.dumps(dict(status='PASS',checkpoint=checkpoint,archive_expected=str(archive))),flush=True)
if __name__=='__main__':main()
