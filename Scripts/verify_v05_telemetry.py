"""Read-only bounded diagnostics audit. CPU samples are not GPU/human benchmarks."""
import argparse,json,statistics,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--task',required=True);p.add_argument('--exe',type=Path);a=p.parse_args();base=ROOT/'Saved/V05'/a.task
    observations=[];records=[]
    modes=['Shop','Placement','Power','Chamber','Events','Quiet','Journey_720','Journey_1080']
    if a.task=='T42':modes=['Error']+modes
    for mode in modes:
        run=json.loads((base/f'latest_{mode}.json').read_text(encoding='utf-8'));assert run['status']=='PASS' and run['telemetry']
        for name in run['telemetry']:
            path=Path(name);data=json.loads(path.read_text(encoding='utf-8'))
            assert data['Automation'] and data['FrameSamples']<=12000 and len(data['Events'])<=512 and path.stat().st_size<1024*1024
            # Runtime FName tables need not preserve the Editor's original spelling.
            entry=next((e['Seconds'] for e in data['Events'] if e['Kind'].casefold()=='entry'),0)
            opened=next((e['Seconds'] for e in data['Events'] if e['Kind'].casefold()=='open'),None)
            records.append(dict(mode=mode,path=str(path),RunId=data['RunId'],Outcome=data['Outcome'],Duration=data['Duration'],FPS=data['FPS'],CpuFrameP95Ms=data['CpuFrameP95Ms'],HitchesOver50ms=data['HitchesOver50ms'],LabLoadSeconds=data['LabLoadSeconds'],HubLoadSeconds=data['HubLoadSeconds'],ScansUsed=data['ScansUsed'],first_box_seconds=opened-entry if opened is not None else None,return_route_seconds=data['ReturnRouteTime']))
        if mode.startswith('Journey'):
            assert run['trips']==3 and run['resolution'][1]==int(mode.split('_')[1])
            rows=records[-3:];assert all(r['first_box_seconds'] is not None for r in rows)
            observations.append(dict(resolution=run['resolution'],mean_duration_seconds=statistics.mean(r['Duration'] for r in rows),cpu_mean_sampled_fps=statistics.mean(r['FPS'] for r in rows),max_p95_ms=max(r['CpuFrameP95Ms'] for r in rows),max_lab_load_seconds=max(r['LabLoadSeconds'] for r in rows),max_hub_load_seconds=max(r['HubLoadSeconds'] for r in rows),mean_first_box_seconds=statistics.mean(r['first_box_seconds'] for r in rows),mean_return_route_seconds=statistics.mean(r['return_route_seconds'] for r in rows)))
    folder=a.exe.parent/'AnomalyLab/Saved/V05/Telemetry' if a.exe else ROOT/'Saved/V05/Telemetry'
    files=[p for p in folder.glob('*.json') if re.fullmatch(r'[a-fA-F0-9]{32}\.json',p.name)]
    assert 0<len(files)<=20 and all(p.stat().st_size<1024*1024 for p in files)
    result=dict(status='PASS',human_samples=0,records=records,walking_observations=observations,retained_files=len(files),scope='Real engine CPU delta sampled at20Hz in synthetic offscreen routes, no GPU benchmark. Initial funds/safe reward/death fixtures; no human pace/balance claim.')
    report=base/'telemetry_audit.json';report.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(dict(status='PASS',report=str(report),records=len(records),human_samples=0)))
if __name__=='__main__':main()
