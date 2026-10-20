"""Audit final source/package/evidence consistency; fail rather than accept stale reports."""
import json, hashlib, struct, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'Saved/V03'
checks=[]
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check(name,value):
    checks.append(dict(check=name,passed=bool(value)))
    assert value,name
package=read(OUT/'package_report.json')
context=read(ROOT/'Saved/CppMigration/latest.json')
work=Path(context['build_workspace'])
try:
    check('Win64 archive succeeded',package['status']=='PASS' and Path(package['exe']).is_file())
    manifest=read(package['source_manifest'])
    for relative,digest in manifest.items():
        check('Current and compiled source '+relative,sha(ROOT/relative)==digest and sha(work/relative)==digest)
    packaged_binary=Path(package['directory'])/'Windows/AnomalyLab/Binaries/Win64/AnomalyLab.exe'
    check('Packaged game binary equals built binary',sha(packaged_binary)==sha(work/'Binaries/Win64/AnomalyLab.exe'))
    for name in ['UnrealEditor-AnomalyLab.dll','UnrealEditor.modules']:
        check('Editor deployed '+name,sha(ROOT/'Binaries/Win64'/name)==sha(work/'Binaries/Win64'/name))
    before=read(ROOT/'Saved/T20/Checkpoint_20261011T202718/我的项目3.uproject')
    check('Project plugin configuration untouched',read(ROOT/'我的项目3.uproject').get('Plugins')==before.get('Plugins'))
    baseline=read(ROOT/'Saved/T20/build_report.json')
    for relative,digest in baseline['protected_sha256'].items():
        if relative.replace('\\','/')=='Content/UI/Menu/WBP_MainMenu.uasset': continue # Intended v0.3 guide update.
        check('Protected asset '+relative,sha(ROOT/relative)==digest)
    check('Legacy map byte-identical',sha(ROOT/'Content/Prototype/Maps/L_LegacyPrototype.umap')==baseline['legacy_sha256'])
    reload=read(OUT/'reload_report.json')
    check('Final independent asset reload',reload['status']=='PASS' and all(c['passed'] for c in reload['checks']))
    screenshots=0
    rendered=[]
    for width,height in [(1280,720),(1920,1080)]:
        summary=read(OUT/f'latest_packaged_render_{width}x{height}.json')
        directory=Path(summary['directory'])
        command=read(directory/'command.json')
        check(f'{width} gameplay exact final executable',Path(command[0])==Path(package['exe']))
        report=read(directory/'runtime_report.json')
        check(f'{width} continuous menu-to-restart itinerary',summary.get('from_menu') and read(directory/'menu_boot_report.json')['status']=='PASS')
        check(f'{width} complete gameplay automation',summary['status']=='PASS' and report['status']=='PASS' and all(c['passed'] for c in report['checks']))
        if width==1920: check('1080p silent visual test', '-nosound' in command)
        for path in directory.glob('*.png'):
            check('Rendered PNG '+path.name+f' {width}',struct.unpack('>II',path.read_bytes()[16:24])==(width,height))
            screenshots+=1
        rendered.append(dict(resolution=[width,height],directory=str(directory),checks=len(report['checks'])))
        menu=read(ROOT/f'Saved/T19Menu/latest_{width}x{height}.json')
        menu_dir=Path(menu['directory'])
        check(f'{width} menu exact final executable',Path(read(menu_dir/'command.json')[0])==Path(package['exe']))
        menu_report=read(menu_dir/'runtime_report.json')
        check(f'{width} menu and normal Level01 travel',menu['status']=='PASS' and menu_report['status']=='PASS' and all(c['passed'] for c in menu_report['checks']))
        for path in menu_dir.glob('*.png'):
            check('Menu rendered PNG '+path.name+f' {width}',struct.unpack('>II',path.read_bytes()[16:24])==(width,height))
            screenshots+=1
    regression=OUT/'Regression'; regression.mkdir(exist_ok=True)
    for target in ['editor','packaged']:
        for suite in ['stats','decision','flow']:
            path=ROOT/f'Saved/T18/{target}_{suite}_report.json'
            result=read(path)
            check(target+' Legacy '+suite,result['status']=='PASS' and all(c['passed'] for c in result['checks']))
            shutil.copy2(path,regression/path.name)
    strategies=[]
    for strategy in ['conservative','greedy','random']:
        summary=read(OUT/f'latest_{strategy}_logic_1280x720.json')
        report=read(Path(summary['directory'])/'runtime_report.json')
        check(strategy+' real bot sample',report['status']=='PASS' and report['strategy']==strategy)
        strategies.append({key:report[key] for key in ['strategy','run_seconds','extracted_value','lost_value','died','scans','rounds']})
    (OUT/'strategy_samples.json').write_text(json.dumps(dict(samples=strategies,scope='One bot run per policy; no human pacing/balance inference; 3-5 minute target pending manual data'),ensure_ascii=False,indent=2),encoding='utf-8')
    status='PASS'
except Exception:
    status='FAIL'
    raise
finally:
    (OUT/'delivery_audit.json').write_text(json.dumps(dict(status=status,checks=checks,package=package),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(status=status,checks=len(checks),source_assets=len(manifest),rendered_screenshots=screenshots,rendered=rendered),ensure_ascii=True))
