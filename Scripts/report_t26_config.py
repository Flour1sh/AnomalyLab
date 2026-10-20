"""Before/after table from actual audited assets and explicit T26 authoring values."""
import json
from pathlib import Path
from t26_data import REGIONS
ROOT=Path(__file__).resolve().parents[1]
baseline=json.loads((ROOT/'Saved/V04/initialization/asset_audit.json').read_text(encoding='utf-8'))['definitions']
lines=['# T26 balance configuration','',
    '2026-10-12 / Asia/Shanghai。首轮可调配置，尚非 T31 最终平衡。基线实际 uasset 已通过独立 UE 只读审计，见 Saved/V04/initialization/asset_audit.json。',
    '', '运行配置：/Game/Prototype/Data/Regions/DA_Region_A、B、C；重建源 Scripts/t26_data.py。L_Prototype 的 RegionRules 明确按 left/middle/right 引用 A/B/C，Legacy 不启用。',
    '', '## 区域权重对照（归一化前）','',
    '| 区域 | 公开型 Safe/Risky/Unknown | 隐藏型 Safe/Medium/Risky | High/Trash/Threat 乘数 | 金额乘数 | 扫描误差增量 | 允许异常 |',
    '|---|---|---|---|---|---|---|',
    '| v0.3 全区 | 1 / 1 / 1 | 1 / 1 / 1 | 1 / 1 / 1 | 1 | 0 | 原追逐者 |']
for r in REGIONS:
    lines.append('| {} | {} | 1 / 1 / 1 | {} / {} / {} | {} | {} | Chaser |'.format(r['region_id'],
        ' / '.join(map(str,r['box_type_weights'])),r['high_value_weight'],r['trash_weight'],r['threat_weight'],r['reward_scale'],r['scan_error_add']))
lines += ['', '每轮独立抽三公开型，若全同型则随机选一个槽，按该区域权重排除原型重抽。故公开型单槽的最终边际概率不同于直接将三权重归一化；统计使用生产 DrawChoices（含修复），不把原权重比例伪称最终百分比。每个区域至少支持两种公开型；本轮三个区域支持全部三种。',
    '', 'Unknown 只在初始化选择一次隐藏配置（当前等权）；下表 Unknown 行为基础参考，实际被隐藏行替代。区域不固定开奖结果。扫描读副本概率/金额范围，OutcomeStream 仅在开箱揭晓时消费；缓存复看不重抽、不重复统计。',
    '', '## 六配置前后（归一化后概率 / 金额范围 / 概率读数误差）','',
    '| 配置 | v0.3 H/T/威胁；金额；误差 | A | B | C |','|---|---|---|---|---|']
records={}
for name,b in baseline.items():
    p=[b[k] for k in ('high_value_chance','trash_chance','threat_chance')]
    format_row=lambda probs,low,high,error: '{:.4f}/{:.4f}/{:.4f}; {}–{}; {:.2f}'.format(*probs,low,high,error)
    values=[format_row(p,b['value_min'],b['value_max'],b['scan_probability_error'])]
    records[name]={}
    for r in REGIONS:
        w=[p[i]*r[k] for i,k in enumerate(('high_value_weight','trash_weight','threat_weight'))]
        probs=[v/sum(w) for v in w]; low=int(b['value_min']*r['reward_scale']+.5); high=int(b['value_max']*r['reward_scale']+.5)
        error=min(1,b['scan_probability_error']+r['scan_error_add'])
        values.append(format_row(probs,low,high,error))
        records[name][r['region_id']]=dict(probabilities=probs,value_min=low,value_max=high,scan_error=error)
    lines.append('| '+name+' | '+' | '.join(values)+' |')
lines += ['', 'H/T/威胁指 HighValue/Trash/Threat，垃圾仍为 $3；金额乘数仅影响高价值整数区间，原 0.9/1.1 或 Unknown 0.7/1.3 扫描金额扩展保留。外观线索概率不改。扫描可靠性仍按隐藏/误差标识高低，不是成功率；B/C 正增量使确定型也显示低可靠性。',
    '', '奖励统计为每次开箱生成物品的面值（Threat=0、Trash=3），不代表拾取、存活或撤离净收益。T26 不模拟死亡率/生存策略；survive 是真实运行中默认威胁自然收容事件计数。',
    '', '## 验证与待测', '',
    '固定种子 26001，生产 DrawChoices + 独立箱 Configuration/Outcome streams，60,000 三箱轮次，每区域 60,000 样本。报告 reward_mean / unbiased sample variance / normal-approximation 95% confidence half-width；威胁率给二项近似 95% 区间。要求相邻区域两类指标区间不重叠。Editor/独立包所有采样 seed/type/hidden/outcome/integer reward 序列摘要、离散统计及缓存读数严格一致；仅派生浮点指标/归一化概率允许 1e-12 相对/绝对误差。每区域/六定义另各 10,000 次开奖频率测试（容差 2 个百分点）。',
    '', '测试执行结果、实际统计和真人状态完成时追加；不得把计划样本数当实际通过。真人取舍体验和音效听感待用户验证，T27–T32 未开始。']
(ROOT/'Docs/v0.4/BALANCE_CONFIG.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(ROOT/'Saved/V04/T26').mkdir(parents=True,exist_ok=True)
(ROOT/'Saved/V04/T26/config_comparison.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print('Wrote before/after table from audited actual assets')
