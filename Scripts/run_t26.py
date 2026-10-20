"""Run native T26 fixed-seed/live-fixture tests and optional rendered HUD checks."""
import argparse,json,subprocess,math
from datetime import datetime
from pathlib import Path
from test_save_slots import new_slot,cleanup_slot
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(); p.add_argument('--exe',type=Path); p.add_argument('--render',action='store_true')
p.add_argument('--width',type=int,default=1280); p.add_argument('--height',type=int,default=720)
p.add_argument('--compare',type=Path,help='Exact comparison with an earlier report.json')
args=p.parse_args()
out=ROOT/'Saved/V04/T26/Runs'/(datetime.now().strftime('%Y%m%dT%H%M%S%f')+('_package' if args.exe else '_editor')+('_render' if args.render else '_logic')+f'_{args.width}x{args.height}')
out.mkdir(parents=True)
slot=new_slot('T26')
cmd=[str(args.exe or Path('E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'))]
if not args.exe: cmd += [str(ROOT/'我的项目3.uproject')]
cmd += ['/Game/Prototype/Maps/L_Prototype']
if not args.exe:
    cmd += ['-game','-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset','-DDC=InstalledNoZenLocalFallback',f'-LocalDataCachePath={ROOT/"Saved/CppMigration/DerivedDataCache"}']
cmd += ['-AnomalyT26Smoke',f'-T26Evidence={out}',f'-AnomalySaveSlot={slot}',f'-abslog={out/"runtime.log"}','-unattended','-nosound','-UTF8Output','-NoScreenMessages']
cmd += ['-RenderOffscreen','-windowed','-ForceRes',f'-ResX={args.width}',f'-ResY={args.height}','-nosplash'] if args.render else ['-nullrhi']
(out/'command.json').write_text(json.dumps(cmd,ensure_ascii=False,indent=2),encoding='utf-8')
print('T26 evidence: '+str(out),flush=True)
try:
    with (out/'stdout.log').open('wb') as f:
        process=subprocess.Popen(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        try: code=process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(); raise RuntimeError('Timed out: '+str(out))
finally:
    removed=cleanup_slot(slot,exe=args.exe)
    (out/'save_isolation.json').write_text(json.dumps(dict(slot=slot,removed=removed),ensure_ascii=False,indent=2),encoding='utf-8')
report_path=out/'report.json'
assert report_path.is_file(),f'Missing report, exit={code}: {out}'
report=json.loads(report_path.read_text(encoding='utf-8-sig'))
assert code==0 and report['status']=='PASS' and all(c['passed'] for c in report['checks']),str(out)
if args.render: assert all((out/(r+'_region.png')).is_file() for r in 'ABC'),'Missing region screenshots'
if args.compare:
    old=json.loads(args.compare.read_text(encoding='utf-8-sig'))
    # Editor/game optimizers can differ by a double ULP (e.g. fused arithmetic).
    # Every sampled seed/type/hidden profile/outcome/integer reward must match exactly.
    assert all(old[key]==report[key] for key in ('seed','round_samples','logical_digest')),'Editor/package gameplay sequence mismatch'
    float_differences=[]
    def compare(a,b,path):
        if isinstance(a,dict):
            assert a.keys()==b.keys(),path
            for k in a: compare(a[k],b[k],path+'/'+k)
        elif isinstance(a,list):
            assert len(a)==len(b),path
            for i,(x,y) in enumerate(zip(a,b)): compare(x,y,path+'/'+str(i))
        elif isinstance(a,float) and isinstance(b,(float,int)):
            assert math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12),f'{path}: {a} != {b}'
            if a!=b: float_differences.append(dict(path=path,editor=a,current=b))
        else: assert a==b,f'{path}: {a} != {b}'
    for key in ('regions','fixture_signatures'):compare(old[key],report[key],key)
    (out/'comparison.json').write_text(json.dumps(dict(status='PASS',logical_digest=report['logical_digest'],
        exact_fields='all sampled seed/type/hidden/outcome/integer reward sequence plus discrete counters and cached reads',
        diagnostic_float_tolerance=dict(relative=1e-12,absolute=1e-12),float_differences=float_differences),ensure_ascii=False,indent=2),encoding='utf-8')
result=dict(status='PASS',directory=str(out),report=str(report_path),checks=len(report['checks']),
    comparison=str(args.compare) if args.compare else None,target='package' if args.exe else 'editor',render=args.render)
(out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Saved/V04/T26'/('latest_'+('package' if args.exe else 'editor')+('_render' if args.render else '_logic')+f'_{args.width}x{args.height}.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
