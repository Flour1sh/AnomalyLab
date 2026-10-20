"""SHA release archive. Verification is read-only; results live outside archives."""
import argparse,json,hashlib,shutil
from package_payload import is_runtime_file
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Saved/V04/T32'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def verify(archive,report_path):
    manifest=json.loads((archive/'release_manifest.json').read_text(encoding='utf-8'));bad=[]
    for r in manifest['files']:
        p=archive/r['path']
        if not p.is_file() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:bad.append(r['path'])
    result=dict(status='FAIL' if bad else 'PASS',archive=str(archive),files=len(manifest['files']),bytes=sum(r['bytes'] for r in manifest['files']),failures=bad,checked_at=datetime.now().astimezone().isoformat(),scope='Read-only SHA-256 verification; no archive file changed.')
    write(report_path,result);assert not bad,result;return result
def project_files():
    for name in ['Source','Config','Content','Scripts','Docs','Binaries/Win64','LowPolyLabPrototype','LowPolyCharacterPrototype','T11EAssets','GameAudio','MenuAudio','ScenePolishAssets']:
        for p in sorted((ROOT/name).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:yield p
    for p in sorted(ROOT.iterdir()):
        if p.is_file() and p.suffix in ['.md','.uproject']:yield p
def create(package,matrix):
    archive=ROOT/'Saved/Releases'/('v0.4_'+package.name+'_HumanPending');archive.mkdir(parents=True,exist_ok=False)
    pkg=json.loads((OUT/'package_report.json').read_text(encoding='utf-8'))
    expected=json.loads(Path(pkg['source_manifest']).read_text(encoding='utf-8'))
    assert all(sha(ROOT/r)==s for r,s in expected.items()),'Packaged source changed'
    records=[];copied=set()
    def copy(src,rel):
        if str(rel) in copied:return
        copied.add(str(rel));dst=archive/rel;dst.parent.mkdir(parents=True,exist_ok=True);digest=sha(src);shutil.copy2(src,dst)
        assert sha(dst)==digest and sha(src)==digest,str(src)
        records.append(dict(path=rel.as_posix(),sha256=digest,bytes=src.stat().st_size,original=str(src)))
    def tree(src,rel,exclude_runtime=False):
        for p in sorted(src.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and not (exclude_runtime and is_runtime_file(p.relative_to(src))):copy(p,rel/p.relative_to(src))
    for src in project_files():copy(src,Path('Project')/src.relative_to(ROOT))
    tree(package/'Windows',Path('Package')/package.name/'Windows',True)
    matrix_report=json.loads((matrix/'report.json').read_text(encoding='utf-8'));assert matrix_report['status']=='PASS'
    assert Path(matrix_report['exe']).resolve()==(package/'Windows/AnomalyLab.exe').resolve(),'Matrix belongs to another package'
    directories={matrix}
    restore=json.loads((OUT/'restore_report.json').read_text(encoding='utf-8'))
    assert restore['status']=='PASS'
    restored=Path(restore['directory'])
    for src in [restored/'copy_manifest.json']+[Path(r['log']) for r in restore['results']]:
        copy(src,Path('Evidence')/src.relative_to(ROOT))
    for r in restore['results']:
        if r.get('result',{}).get('directory'):directories.add(Path(r['result']['directory']))
    for result in matrix_report['results']:
        data=result['result']
        if data and data.get('directory'):directories.add(Path(data['directory']))
        if data and data.get('results'):
            directories.update(Path(r['directory']) for r in data['results'])
    # Reproduction baselines plus final Editor evidence are retained with original relative paths.
    directories.update([ROOT/'Saved/V04/T26/Runs/20261012T094412728513_editor_logic_1280x720',ROOT/'Saved/V04/T31/Runs/20261012T094855549302_editor',ROOT/'Saved/V03/Runs/20261012T094419802773_render_1280x720',ROOT/'Saved/V03/Runs/20261012T095242925418_render_1920x1080',ROOT/'Saved/T19Menu/RenderRuns/20261013T131615_1280x720',ROOT/'Saved/T19Menu/RenderRuns/20261013T131613_1920x1080'])
    for src in sorted((ROOT/'Saved/V03').glob('latest_*.json')):
        data=json.loads(src.read_text(encoding='utf-8'))
        if data.get('directory') and '095242925418' in data['directory']:directories.add(Path(data['directory']))
    editor_suite=OUT/'editor_save_suite.json'
    if editor_suite.exists():
        suite=json.loads(editor_suite.read_text(encoding='utf-8'));directories.update(Path(r['directory']) for r in suite['results'])
    for directory in sorted(directories):
        assert directory.resolve().is_relative_to(ROOT/'Saved');tree(directory,Path('Evidence')/directory.relative_to(ROOT))
    visual=json.loads((OUT/'visual_review.json').read_text(encoding='utf-8'))
    for name in visual['viewed']:copy(ROOT/name,Path('Evidence')/name)
    for name in ['Matrix_20261012T095754948621','Matrix_20261013T132043485221']:
        tree(OUT/name,Path('Evidence/Saved/V04/T32')/name)
    for stage in ['T26','T27','T28','T29','T30','T31','T32']:
        for src in (ROOT/'Saved/V04'/stage).glob('*.json'):copy(src,Path('Evidence')/src.relative_to(ROOT))
    for src in (ROOT/'Saved/V04').glob('checkpoint_*.json'):copy(src,Path('Evidence')/src.relative_to(ROOT))
    build_logs=sorted((ROOT/'Saved/CppMigration/20260929T083920372566Z').glob('build-editor_*.log'))
    for name in ['build-editor_20261012T014735269928Z.log','build-editor_20261012T021044438788Z.log',build_logs[-1].name,Path(pkg['log']).name]:
        src=ROOT/'Saved/CppMigration/20260929T083920372566Z'/name
        if src.exists():copy(src,Path('Evidence')/src.relative_to(ROOT))
    text='''# v0.4 engineering RC / HUMAN_PENDING

Project/ contains source, assets, scripts, documents, Editor binaries and original model/audio generation sources.
Package/ contains the ENTIRE Windows directory. Copy all of it; launch AnomalyLab.exe normally.
Evidence/Saved/ contains final packaged/Editor reports, real frames, fixed-seed baselines and restoration proof.
Human samples: 0. PLAYTEST_RECORD.md is an unexecuted procedure/template, not completed human evidence.

Restore Project/ into a NEW folder. Never overlay an older checkpoint on a newer project.
Use UE 5.8 and the existing engine editor plugins; rebuild via Scripts/cpp_migration.py with a NEW configured ASCII workspace rather than relying on its original absolute context.
To configure a relocated source checkout, create a new Project/Saved/CppMigration/<new-id>/ directory, then write Project/Saved/CppMigration/latest.json with two absolute paths:
{"directory":"F:/AnomalyLab/Restored_v04/Saved/CppMigration/Recovery_NEW_ID","build_workspace":"F:/AnomalyLab/CppBuildWork/Recovery_NEW_ID"}
Replace the example checkout path with your restored folder. The build_workspace path must be ASCII, writable and NEW; do not reuse the original work directory. Check ENGINE in Scripts/cpp_migration.py matches your UE5.8 installation. Close UE before running `python Scripts/cpp_migration.py build-editor` from the restored project. The old `prepare` mode depends on historical P0 evidence and is not the recovery initializer.
For immediate play use Package/Windows; source recompilation needs UE5.8/MSVC14.44/WindowsSDK10.0.22621.0. Copy Evidence/Saved into restored Project/Saved to reproduce historical comparison baselines; personal SaveGames are not included.
Save default: AnomalyLab_Meta_v04; observe actual [MetaSave] path. Back up personal .sav/.bak separately before changing builds.

Read-only verify: python Scripts/archive_v04_rc.py --verify <archive>
Verification results are written to the calling workspace Saved/V04/T32, never back into this archive.
SHA manifest covers payload and this README, excluding manifest itself. Same-disk recovery copy, not offsite backup.
Accepted v0.3 remains separately preserved. New RC is not Human Accepted.
'''
    text=text.replace('Package/Windows',f'Package/{package.name}/Windows')
    readme=archive/'README_RESTORE.md';readme.write_text(text,encoding='utf-8');records.append(dict(path='README_RESTORE.md',sha256=sha(readme),bytes=readme.stat().st_size,original=None))
    write(archive/'release_manifest.json',dict(release=package.name,status='AUTOMATED_VISUAL_VERIFIED_HUMAN_PENDING',created_at=datetime.now().astimezone().isoformat(),package_source_files=len(expected),files=records))
    result=verify(archive,OUT/'archive_verification.json');write(OUT/'release_archive.json',result);return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',type=Path);p.add_argument('--package',type=Path);p.add_argument('--matrix',type=Path);a=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    if a.verify:result=verify(a.verify.resolve(),OUT/('readonly_verify_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'.json'))
    else:
        assert a.package and a.matrix;result=create(a.package.resolve(),a.matrix.resolve())
    print(json.dumps(result,ensure_ascii=True))
