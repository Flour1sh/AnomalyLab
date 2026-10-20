"""Final consistency checks for the scene-only upgrade and its real packaged run."""
from pathlib import Path
import json,hashlib,struct,shutil
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'Saved/ScenePolish'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks=[]
def check(name,value):
    checks.append(dict(check=name,passed=bool(value)));assert value,name
package=read(ROOT/'Saved/V03/package_report.json')
baseline=read(OUT/'baseline.json');context=read(ROOT/'Saved/CppMigration/latest.json')
work=Path(context['build_workspace'])
try:
    check('New Win64 package succeeded',package['status']=='PASS' and Path(package['exe']).is_file()
          and 'RC_20261011T220432' not in package['exe'])
    manifest=read(package['source_manifest'])
    for relative,digest in manifest.items():check('Source/build snapshot '+relative,sha(ROOT/relative)==digest and sha(work/relative)==digest)
    check('New environment assets included',sum('Environment\\ScenePolish\\' in p.replace('/','\\') for p in manifest)==25)
    binary=Path(package['directory'])/'Windows/AnomalyLab/Binaries/Win64/AnomalyLab.exe'
    check('Packaged binary matches compiled binary',sha(binary)==sha(work/'Binaries/Win64/AnomalyLab.exe'))
    for folder in ['Source','Config']:
        files=[p for p in (Path(baseline['backup'])/folder).rglob('*') if p.is_file()]
        check('Accepted '+folder+' unchanged',all(sha(p)==sha(ROOT/p.relative_to(Path(baseline['backup']))) for p in files))
    check('All 1045 accepted assets unchanged',len(baseline['protected'])==1045 and all(sha(ROOT/relative)==digest for relative,digest in baseline['protected'].items()))
    check('Exploration map deliberately updated',sha(ROOT/'Content/Prototype/Maps/L_Prototype.umap')!=baseline['map_sha256'])
    build=read(OUT/'build_report.json');reload=read(OUT/'reload_report.json');fbx=read(OUT/'fbx_reload.json')
    check('Independent UE reload and navigation',reload['status']=='PASS' and all(c['passed'] for c in reload['checks']) and reload['navigation_valid_tiles']>0)
    check('Independent exported FBX verification',fbx['status']=='PASS' and len(fbx['checks'])==12 and all(c['passed'] for c in fbx['checks']))
    check('Repeated generator retains unique object set',build['generated_actors']==reload['generated_actors']==180)
    capture=read(OUT/'capture_report.json');viewdir=Path(capture['directory'])
    check('Five rendered level photographs',capture['status']=='PASS' and len(list(viewdir.glob('*.png')))==5)
    for p in viewdir.glob('*.png'):check('Photograph dimensions '+p.name,struct.unpack('>II',p.read_bytes()[16:24])==(1600,900))
    summary=read(ROOT/'Saved/V03/latest_packaged_render_1280x720.json');rundir=Path(summary['directory'])
    command=read(rundir/'command.json');runtime=read(rundir/'runtime_report.json');menu=read(rundir/'menu_boot_report.json')
    check('Runtime uses exact new executable',Path(command[0])==Path(package['exe']))
    check('New package complete gameplay regression',summary['status']=='PASS' and runtime['status']=='PASS' and all(c['passed'] for c in runtime['checks']))
    check('Normal default menu to gameplay travel',summary['from_menu'] and menu['status']=='PASS' and all(c['passed'] for c in menu['checks']))
    gamepng=list(rundir.glob('*.png'))
    check('Real packaged render evidence',len(gamepng)>=18)
    for p in gamepng:check('Game PNG '+p.name,struct.unpack('>II',p.read_bytes()[16:24])==(1280,720))
    (OUT/'runtime_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copy2(rundir/'runtime_report.json',OUT/'runtime_report.json')
    status='PASS'
except Exception:
    status='FAIL';raise
finally:
    (OUT/'delivery_audit.json').write_text(json.dumps(dict(status=status,checks=checks,package=package),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(status=status,checks=len(checks),protected_assets=len(baseline['protected']),source_assets=len(manifest),runtime_checks=len(runtime['checks']),photographs=5,game_screenshots=len(gamepng)),ensure_ascii=True))
