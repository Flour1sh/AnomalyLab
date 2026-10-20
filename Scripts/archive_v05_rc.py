"""Create immutable complete v0.5 recovery payload; verification never writes into archive."""
import argparse,json,shutil,os,stat
from pathlib import Path
from datetime import datetime
from checkpoint_v05 import ROOT,files,sha,write
from package_payload import is_runtime_file
BASE=ROOT/'Saved/V05/T42'
def verify(archive):
    manifest=json.loads((archive/'release_manifest.json').read_text(encoding='utf-8'))
    expected={r['path'] for r in manifest['files']}
    actual={p.relative_to(archive).as_posix() for p in archive.rglob('*') if p.is_file()}-{'release_manifest.json'}
    bad=sorted(expected^actual)+[r['path'] for r in manifest['files'] if not (archive/r['path']).is_file() or (archive/r['path']).stat().st_size!=r['bytes'] or sha(archive/r['path'])!=r['sha256']]
    readonly=all(not (p.stat().st_mode & stat.S_IWRITE) for p in archive.rglob('*') if p.is_file())
    result=dict(status='FAIL' if bad else 'PASS',archive=str(archive),files=len(expected),bytes=sum(r['bytes'] for r in manifest['files']),failures=bad,read_only_files=readonly,checked_at=datetime.now().astimezone().isoformat(),scope='Read-only SHA/inventory verification, no writes to archive')
    write(BASE/('archive_verify_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'.json'),result);assert not bad,result;return result
def create():
    pkg=json.loads((BASE/'package_report.json').read_text(encoding='utf-8'));matrix=json.loads(Path(json.loads((BASE/'latest_matrix.json').read_text(encoding='utf-8'))['report']).read_text(encoding='utf-8'));restore=json.loads((BASE/'restore_report.json').read_text(encoding='utf-8'))
    assert pkg['status']==matrix['status']==restore['status']=='PASS'
    clean=json.loads((BASE/'clean_package.json').read_text(encoding='utf-8'));assert clean['status']=='PASS'
    assert Path(matrix['exe']).resolve()==Path(pkg['exe']).resolve()
    assert all(sha(ROOT/p)==h for p,h in json.loads(Path(pkg['source_manifest']).read_text(encoding='utf-8')).items())
    name=Path(pkg['directory']).name;archive=ROOT/'Saved/Releases'/('v0.5_'+name+'_HumanPending');archive.mkdir(parents=True,exist_ok=False);records=[];done=set()
    def copy(src,rel):
        if rel.as_posix() in done:return
        done.add(rel.as_posix());dest=archive/rel;dest.parent.mkdir(parents=True,exist_ok=True);h=sha(src);shutil.copy2(src,dest);assert sha(dest)==h and sha(src)==h
        records.append(dict(path=rel.as_posix(),bytes=src.stat().st_size,sha256=h))
    def tree(src,rel,package=False):
        for p in sorted(src.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and not (package and is_runtime_file(p.relative_to(src))):copy(p,rel/p.relative_to(src))
    for p in files(ROOT):copy(p,Path('Project')/p.relative_to(ROOT))
    assert not (Path(clean['exe']).parent/'AnomalyLab/Saved').exists()
    tree(Path(clean['exe']).parent,Path('Package/Windows'),True)
    # Keep all stage successes and failures; avoid copying baseline binaries or restored duplicate payloads.
    for stage in range(33,43):
        src=ROOT/f'Saved/V05/T{stage}'
        for p in sorted(src.rglob('*')):
            rel=p.relative_to(src)
            if not p.is_file() or rel.parts[0]=='BaselinePackage' or rel.parts[0].startswith('Restore_') or '__pycache__' in rel.parts:continue
            copy(p,Path('Evidence')/p.relative_to(ROOT))
    for p in (ROOT/'Saved/V05').glob('checkpoint_*_verified.json'):copy(p,Path('Evidence')/p.relative_to(ROOT))
    # Old suites store their real frames and reports outside Saved/V05. Follow report references.
    seen=set()
    def collect(data):
        if isinstance(data,list):
            for v in data:collect(v)
        elif isinstance(data,dict):
            for key,value in data.items():
                if key in ['report','directory','log','runner_log'] and isinstance(value,str):
                    path=Path(value)
                    if not path.is_absolute() or not path.resolve().is_relative_to(ROOT/'Saved') or not path.exists():continue
                    if 'Checkpoint_' in str(path) or 'BuildWork' in str(path):continue
                    if path.is_file():copy(path,Path('Evidence')/path.relative_to(ROOT))
                    elif key=='directory':tree(path,Path('Evidence')/path.relative_to(ROOT))
                    if path.is_file() and path.suffix=='.json' and str(path) not in seen:
                        seen.add(str(path));collect(json.loads(path.read_text(encoding='utf-8-sig')))
                elif isinstance(value,(dict,list)):collect(value)
    collect(matrix)
    t41=json.loads((ROOT/'Saved/V05/T41/latest_gate.json').read_text(encoding='utf-8'));collect(json.loads(Path(t41['report']).read_text(encoding='utf-8')))
    restored=Path(restore['directory']);copy(restored/'copy_manifest.json',Path('Evidence')/(restored/'copy_manifest.json').relative_to(ROOT))
    collect(restore['results'])
    for p in (ROOT/'Saved/CppMigration/V05_T34_20261013T190745').glob('*.log'):copy(p,Path('Evidence')/p.relative_to(ROOT))
    for p in (ROOT/'Saved/CppMigration/V05_T34_20261013T190745').glob('*.jsonl'):copy(p,Path('Evidence')/p.relative_to(ROOT))
    readme=archive/'README_RESTORE.md';readme.write_text('''# AnomalyLab v0.5 / Engineering Verified / Awaiting Human Validation

Project/ is the complete source/Config/Content/scripts/docs/Editor binaries/model/audio source tree.
Package/Windows/ is the ENTIRE playable Windows package. Copy all of it to a NEW directory and launch AnomalyLab.exe normally.
Evidence/ retains stage gates, raw failures, logs, actual D3D12 frames, telemetry, full packaged matrix and restoration proof.
Human samples:0. Use Project/Docs/v0.5/HUMAN_TEST_GUIDE.md and PLAYTEST_RECORD.md; no HumanAccepted claim.

Restore Project/ into a NEW folder. Do not overlay a checkpoint on a later project.
Archive files have Windows read-only attributes. For editing a restored Project, clear those attributes only on the NEW copy; keep this archive unchanged.
UE5.8/MSVC14.44/WindowsSDK10.0.22621.0 are needed to rebuild source. Engine path in Scripts/cpp_migration.py must match installation.
Create NEW Project/Saved/CppMigration/Recovery_NEW_ID and write Project/Saved/CppMigration/latest.json with absolute directory and a NEW ASCII build_workspace inside Project/Saved/BuildWork. Close UE and run python Scripts/cpp_migration.py build-editor. Do not use historical prepare or original v0.4 build context.
Example latest.json (replace both paths): {"directory":"F:/RestoredV05/Saved/CppMigration/Recovery_NEW_ID","build_workspace":"F:/RestoredV05/Saved/BuildWork/Recovery_NEW_ID"}
Immediate play needs the whole Package/Windows, not source recompilation. Restored source Editor Hub and package three-trip Journey were actually tested.
Personal SaveGames/caches/runtime package files are excluded. Preserve personal sav/bak separately. Default slot remains AnomalyLab_Meta_v04; actual path is logged [MetaSave]. See SAVE_MIGRATION.md for explicit import to an empty target.
Accepted v0.4 RC/archives/code/assets were never modified. Four externally maintained original Docs changes have pinned SHA evidence and retained strict identity FAIL.

Read-only verify: python Scripts/archive_v05_rc.py --verify <archive> from an active workspace, not this archive.
Results are written to the calling workspace Saved/V05/T42, never into the archive. SHA manifest covers payload and README, excluding itself.
Same-disk recovery copy; not an offsite backup.
''',encoding='utf-8');records.append(dict(path='README_RESTORE.md',bytes=readme.stat().st_size,sha256=sha(readme)))
    write(archive/'release_manifest.json',dict(release=name,status='ENGINEERING_VERIFIED_AWAITING_HUMAN_VALIDATION',created_at=datetime.now().astimezone().isoformat(),human_samples=0,files=records))
    assert archive.resolve().is_relative_to((ROOT/'Saved/Releases').resolve()) and archive.name.startswith('v0.5_')
    for p in archive.rglob('*'):
        if p.is_file():os.chmod(p,stat.S_IREAD)
    result=verify(archive);write(BASE/'release_archive.json',result);return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',type=Path);a=p.parse_args();BASE.mkdir(parents=True,exist_ok=True);print(json.dumps(verify(a.verify.resolve()) if a.verify else create(),ensure_ascii=True),flush=True)
