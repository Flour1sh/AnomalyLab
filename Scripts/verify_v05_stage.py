"""Sequential per-stage gates, reports and complete SHA snapshots. Never packages."""
import argparse,json,os,subprocess,sys,hashlib
from pathlib import Path
from datetime import datetime
from test_save_slots import new_slot,cleanup_slot
from checkpoint_v05 import create,protected,write
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--task',required=True);p.add_argument('--skip-loop',action='store_true');p.add_argument('--modes',nargs='*',default=[]);p.add_argument('--reuse-modes',nargs='*',default=[]);p.add_argument('--groups',nargs='+'); a=p.parse_args()
    assert a.task in ['T35','T36','T37','T38','T39','T40','T41']
    out=ROOT/'Saved/V05'/a.task/('Gate_'+datetime.now().strftime('%Y%m%dT%H%M%S'));out.mkdir(parents=True)
    results=[];module=hashlib.sha256((ROOT/'Binaries/Win64/UnrealEditor-AnomalyLab.dll').read_bytes()).hexdigest()
    env=os.environ.copy();env['PYTHONIOENCODING']='utf-8';env['PYTHONDONTWRITEBYTECODE']='1'
    def job(name,args,timeout=1200):
        cmd=[sys.executable,str(ROOT/'Scripts'/args[0])]+args[1:];log=out/(name+'.log');write(out/(name+'_command.json'),cmd)
        print('START '+name,flush=True)
        with log.open('wb') as f: process=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=timeout)
        data=None
        for line in log.read_text(encoding='utf-8',errors='replace').splitlines():
            try:
                v=json.loads(line)
                if isinstance(v,dict) and v.get('status'):data=v
            except ValueError:pass
        good=process.returncode==0 and data is not None and data['status']=='PASS'
        results.append(dict(name=name,status='PASS' if good else 'FAIL',exit_code=process.returncode,result=data,log=str(log)))
        write(out/'report.json',dict(status='RUNNING' if good else 'FAIL',task=a.task,module_sha256=module,results=results,human_samples=0))
        print(json.dumps(dict(name=name,status=results[-1]['status'])),flush=True)
        assert good,str(log)
        return data
    if a.skip_loop:
        previous=json.loads((ROOT/'Saved/V05'/a.task/'latest_Loop.json').read_text(encoding='utf-8'))
        assert previous['status']=='PASS' and previous['module_sha256']==module
        results.append(dict(name='Loop',status='PASS',exit_code=0,result=previous))
    else:job('Loop',['run_v05.py','--task',a.task,'--mode','Loop','--render'])
    for mode in ['Direct']+(['Import','Corrupt'] if a.task=='T35' else [])+a.modes:
        if mode in a.reuse_modes:
            previous=json.loads((ROOT/'Saved/V05'/a.task/f'latest_{mode}.json').read_text(encoding='utf-8'))
            assert previous['status']=='PASS' and previous['module_sha256']==module
            raw=json.loads(Path(previous['report']).read_text(encoding='utf-8-sig'));assert all(c['passed'] for c in raw['checks'])
            results.append(dict(name=mode,status='PASS',exit_code=0,result=previous));continue
        args=['run_v05.py','--task',a.task,'--mode',mode]
        if mode in a.modes:args+=['--render']
        job(mode,args)
    if a.task in ['T35','T36','T41']:
        slot=new_slot(a.task+'Restart')
        try:
            job('RestartWrite',['run_v05.py','--task',a.task,'--mode','RestartWrite','--slot',slot,'--keep-slot'])
            job('RestartRead',['run_v05.py','--task',a.task,'--mode','RestartRead','--slot',slot])
        finally:cleanup_slot(slot)
    if a.task=='T41':
        job('Journey1080',['run_v05.py','--task',a.task,'--mode','Journey','--render','--width','1920','--height','1080'])
        job('TelemetryDisabled',['run_v05.py','--task',a.task,'--mode','Loop','--no-telemetry'])
        job('TelemetryAudit',['verify_v05_telemetry.py','--task',a.task])
    args=['run_v05_baseline.py','--target','editor','--task',a.task]
    if a.groups:args+=['--groups']+a.groups
    job('regression',args)
    assert hashlib.sha256((ROOT/'Binaries/Win64/UnrealEditor-AnomalyLab.dll').read_bytes()).hexdigest()==module,'No code rebuild during stage gate'
    audit=protected(a.task)
    if a.task=='T37':
        for name in ['placement_build.json','placement_reload.json']:
            asset=json.loads((ROOT/'Saved/V05/T37'/name).read_text(encoding='utf-8'));assert asset['status']=='PASS'
            results.append(dict(name=name,status='PASS',exit_code=0,result=asset))
    if a.task=='T38':
        for name in ['power_build.json','environment_reload.json']:
            asset=json.loads((ROOT/'Saved/V05/T38'/name).read_text(encoding='utf-8'));assert asset['status']=='PASS'
            results.append(dict(name=name,status='PASS',exit_code=0,result=asset))
    if a.task=='T39':
        for name in ['chamber_build.json','environment_reload.json']:
            asset=json.loads((ROOT/'Saved/V05/T39'/name).read_text(encoding='utf-8'));assert asset['status']=='PASS'
            results.append(dict(name=name,status='PASS',exit_code=0,result=asset))
    if a.task=='T40':
        for name in ['events_build.json','environment_reload.json']:
            asset=json.loads((ROOT/'Saved/V05/T40'/name).read_text(encoding='utf-8'));assert asset['status']=='PASS'
            results.append(dict(name=name,status='PASS',exit_code=0,result=asset))
    if a.task=='T41':
        for name in ['ui_polish.json','environment_reload.json','telemetry_audit.json']:
            asset=json.loads((ROOT/'Saved/V05/T41'/name).read_text(encoding='utf-8'));assert asset['status']=='PASS'
            results.append(dict(name=name,status='PASS',exit_code=0,result=dict(report=str(ROOT/'Saved/V05/T41'/name))))
    baseline=json.loads((ROOT/'Saved/V05/T33/source_copy_manifest.json').read_text(encoding='utf-8'))
    from checkpoint_v05 import sha
    content=[r for r in baseline['files'] if r['path'].startswith('Content/')]
    assert all(sha(ROOT/r['path'])==r['sha256'] for r in content)
    final=dict(status='PASS',task=a.task,module_sha256=module,results=results,protected_content=len(content),protected_report=str(ROOT/'Saved/V05'/a.task/'protected_after.json'),human_samples=0,packaged=False)
    write(out/'report.json',final);write(ROOT/'Saved/V05'/a.task/'latest_gate.json',dict(status='PASS',report=str(out/'report.json')))
    report=f'# {a.task} 工程阶段报告\n\n完成时间：{datetime.now().astimezone().isoformat()}。自动化门槛PASS；最终闭环以Saved/V05/checkpoint_{a.task}_verified.json为PASS为准。\n\n'
    report+='本阶段设计与改动见'+a.task+'_PLAN.md及ARCHITECTURE_MAP/DECISIONS。永久经济仍为Progression/Schema2，本任务未修改v0.4原工程或旧Content。\n\n'
    report+='| 验证 | 结果 | 证据 |\n|---|---|---|\n'
    for r in results:report+=f"| {r['name']} | {r['status']} | {r['result'].get('report',r['result'].get('directory',''))} |\n"
    report+=f'\n模块SHA：{module}。完整命令/日志/结果：{out.as_posix()}/report.json。原1081 Content、原工程非文档载荷及RC/归档全集合SHA不变；原工程4份外部维护文档变化单独保留证据Saved/V05/T35/external_baseline_document_changes.json（严格原字节身份审计FAIL保留，未重设原清单）。隔离Automation_存档；真人样本0。本阶段未打包，统一人工输入/画面/听感/平衡测试待T42交付用户。失败记录保留，不覆写历史报告。\n'
    if a.task=='T35':report+='\n真实三次往返覆盖51断言：成功123只入账一次、同帧死亡损失456无入账、保存故障Error无假兑现。出发保存失败不扣费；重复launch/claim/settle拒绝，冻结装备生效。首次扫描断言误用基础maximum而非remaining，且组件BeginPlay资源覆盖需延后初始化；已修正并真实重跑。初始新增cpp链接及装备枚举编译失败日志保留。显式-AnomalyImportSave读取旧档并验证，目标无档才导入；未对玩家实际旧档执行导入。\n'
    if a.task=='T41':
        metrics=json.loads((ROOT/'Saved/V05/T41/telemetry_audit.json').read_text(encoding='utf-8'))
        report+='\n新增Telemetry、LoadingWidget和独立Journey输入驱动；生产默认菜单、W真实碰撞步行、商店四项购买、Q扫描、E开箱/实体拾取、物理返程和三次往返通过，无瞬移。初始币、安全奖励和致死分支为明示夹具，不能当作自然局长/平衡。商店初始空档文案及设备面朝向已修正。地图生成两次幂等、全新进程重载通过。\n\n'
        report+='诊断文件限20、每文件≤450000字符、事件≤512、CPU帧样本≤12000，写临时文件后替换；关闭统计的同一经济测试仍PASS。扫描、箱位、事件和反制、伤害、收益/损失、出入时间与加载实际采集。原始指标Saved/V05/T41/telemetry_audit.json。\n\n'
        for row in metrics['walking_observations']:report+=f"自动步行{row['resolution']}：平均局内{row['mean_duration_seconds']:.2f}秒，采样CPU平均FPS{row['cpu_mean_sampled_fps']:.2f}、最大P95帧耗{row['max_p95_ms']:.2f}ms，最大Lab加载{row['max_lab_load_seconds']:.3f}秒、Hub加载{row['max_hub_load_seconds']:.3f}秒。\n\n"
        report+='以上为20Hz抽样的实际CPU帧间隔及短自动路线，含真实加载/截图开销，不是GPU基准或真人3–5分钟目标。真人听感、操作、公平性、设备使用倾向与5人×3局均待用户最终统一验证。\n'
    (ROOT/'Docs/v0.5'/f'{a.task}_REPORT.md').write_text(report,encoding='utf-8')
    (ROOT/'Docs/v0.5/progress.md').write_text(f'# v0.5 Progress\n\nBaseline: v0.4 RC_20261013T131738\nCurrent Task: {a.task}\nStatus: Verified (checkpoint index must be PASS)\n\n阶段证据见{a.task}_REPORT.md。用户已授权顺序T35–T42；各阶段自动测试和相关旧回归PASS后推进。真人测试由用户最终统一执行。当前未打包；恢复点Saved/V05/checkpoint_{a.task}_verified.json。\n',encoding='utf-8')
    state=f'# CURRENT IMPLEMENTATION STATE\n\n{datetime.now().astimezone().isoformat()} / Asia/Shanghai，v0.5独立工作副本F:/AnomalyLab/AnomalyLab_v05，当前{a.task}工程验证通过。恢复闭环以Saved/V05/checkpoint_{a.task}_verified.json为PASS为准。\n\n默认菜单→独立安全L_Hub→确认出发→独立L_Lab；真实RunId/装备冻结/一次消费/一次结算/死亡优先/返回只读战报。Schema2永久经济由Progression唯一管理，Lab无购物，退出不兑现。实际已完成范围/证据见Docs/v0.5/{a.task}_REPORT.md及此前阶段报告，后续计划不当作实现。\n\n用户授权连续T35–T42，每阶段自动测试/相关旧回归通过后推进，全部通过后T42打包，最终统一人工测试。真人样本0，未HumanAccepted。T33/T34及后续恢复点保留。原1081旧Content、原工程非文档载荷、已验收RC/v0.3/v0.4归档不变；原工程4份外部维护文档变化固定SHA记录在T35/external_baseline_document_changes.json，原严格身份FAIL保留，本任务不写基线。\n'
    (ROOT/'Docs/STATE.md').write_text(state,encoding='utf-8')
    matrix=ROOT/'Docs/v0.5/TEST_MATRIX.md';lines=matrix.read_text(encoding='utf-8').splitlines()
    for i,line in enumerate(lines):
        for number in range(35,int(a.task[1:])+1):
            label='T'+str(number);index=ROOT/'Saved/V05'/label/'latest_gate.json'
            if line.startswith('| '+label+' |') and index.exists():
                parts=line.split('|');parts[-2]=f' PASS: {label}_REPORT.md / per-stage automated gates and relevant regression; final human testing pending ';lines[i]='|'.join(parts)
    matrix.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    checkpoint=create(a.task+'_verified',a.task)
    write(ROOT/'Saved/V05'/a.task/'delivery_summary.json',dict(status='PASS',report=str(out/'report.json'),checkpoint=checkpoint,human_samples=0))
    print(json.dumps(dict(status='PASS',task=a.task,report=str(out/'report.json'),checkpoint=checkpoint)),flush=True)

if __name__=='__main__':main()
