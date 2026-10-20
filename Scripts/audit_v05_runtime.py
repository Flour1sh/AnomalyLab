"""Read actual selected runtime logs for fatal/Blueprint failures; preserve known ensures."""
import argparse,json,re
from pathlib import Path
from checkpoint_v05 import ROOT,write
def main():
    p=argparse.ArgumentParser();p.add_argument('--task',required=True);p.add_argument('--exe',type=Path);a=p.parse_args();base=ROOT/'Saved/V05'/a.task
    rows=[];failures=[];seen=set()
    for index in base.glob('latest_*.json'):
        obj=json.loads(index.read_text(encoding='utf-8'))
        if not obj.get('directory'):continue
        log=Path(obj['directory'])/'runtime.log'
        if not log.exists() or str(log) in seen:continue
        seen.add(str(log));text=log.read_text(encoding='utf-8',errors='replace')
        fatal=[line for line in text.splitlines() if re.search(r'Fatal error:|Unhandled Exception|Blueprint Runtime Error|Assertion failed:',line)]
        failures.extend(dict(log=str(log),signal=line) for line in fatal)
        rows.append(dict(log=str(log),fatal_or_blueprint_errors=len(fatal),handled_ensure_count=text.count('Ensure condition failed:'),gamefeature_baseline_signal='GameFeatures.GameFeatureData' in text))
    result=dict(status='FAIL' if failures else 'PASS',logs=len(rows),rows=rows,failures=failures,scope='Latest selected mode/resolution logs only. Raw failures and handled ensure signals retained; not a universal absence-of-bugs claim.')
    report=base/'runtime_signal_audit.json';write(report,result);assert rows and not failures,str(report);print(json.dumps(dict(status='PASS',report=str(report),logs=len(rows))),flush=True)
if __name__=='__main__':main()
