"""T33 only: create an isolated work copy, never write to accepted originals."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT.parent / '我的项目3'
RELEASE = 'AnomalyLab_v04_RC_20261013T131738'
ARCHIVE = ORIGINAL / 'Saved/Releases' / ('v0.4_' + RELEASE + '_HumanPending')
RC = ORIGINAL / 'Builds/v0.4' / RELEASE / 'Windows'
OUT = ROOT / 'Saved/V05/T33'
FOLDERS = ('Source','Config','Content','Scripts','Docs','Binaries/Win64',
           'LowPolyLabPrototype','LowPolyCharacterPrototype','T11EAssets',
           'GameAudio','MenuAudio','ScenePolishAssets')

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(4*1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def write(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def tree(path):
    return {p.relative_to(path).as_posix():sha(p) for p in sorted(path.rglob('*')) if p.is_file()}

def project_files():
    for folder in FOLDERS:
        for p in sorted((ORIGINAL/folder).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts: yield p
    for p in sorted(ORIGINAL.iterdir()):
        if p.is_file() and p.suffix in ('.md','.uproject'): yield p

def main():
    assert ORIGINAL.is_dir() and RC.is_dir() and ARCHIVE.is_dir()
    assert not (OUT/'bootstrap.json').exists(), 'Already initialized: do not overlay'
    OUT.mkdir(parents=True, exist_ok=True)
    accepted=json.loads((ORIGINAL/'Saved/V04/accepted_release.json').read_text(encoding='utf-8'))
    assert accepted['release']==RELEASE and accepted['engineering_manifest_sha256']==sha(ARCHIVE/'release_manifest.json')
    manifest=json.loads((ARCHIVE/'release_manifest.json').read_text(encoding='utf-8'))
    bad=[r['path'] for r in manifest['files'] if not (ARCHIVE/r['path']).is_file()
         or (ARCHIVE/r['path']).stat().st_size!=r['bytes'] or sha(ARCHIVE/r['path'])!=r['sha256']]
    write(OUT/'archive_readonly_verify.json',dict(status='FAIL' if bad else 'PASS',files=len(manifest['files']),failures=bad))
    assert not bad, bad
    protected={str(p):tree(p) for p in (ARCHIVE,RC,ORIGINAL/'Saved/Releases/v0.3_ScenePolish_Accepted_20261011',ORIGINAL/'Builds/v0.3/AnomalyLab_RC_20261011T225958/Windows')}
    records=[]
    for src in project_files():
        rel=src.relative_to(ORIGINAL); dst=ROOT/rel
        assert not dst.exists(), str(dst)
        digest=sha(src); dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
        assert sha(dst)==digest and sha(src)==digest, str(rel)
        records.append(dict(path=rel.as_posix(),sha256=digest,bytes=src.stat().st_size))
    write(OUT/'source_copy_manifest.json',dict(files=records,original=str(ORIGINAL),target=str(ROOT)))
    expected={r['path'][len('Project/'):]:r['sha256'] for r in manifest['files'] if r['path'].startswith('Project/')}
    deltas=[r['path'] for r in records if r['path'] in expected and r['sha256']!=expected[r['path']]]
    core=[p for p in deltas if p.startswith(('Source/','Content/','Config/','Binaries/'))]
    missing=[p for p in expected if p.startswith(('Source/','Content/','Config/')) and not (ROOT/p).exists()]
    assert not core and not missing, (core,missing)
    # Tests run this mutable copy of the RC. Runtime output cannot touch RC/archives.
    package=OUT/'BaselinePackage/Windows'
    shutil.copytree(RC,package,ignore=lambda d,n: ['Saved'] if Path(d).name in ('AnomalyLab','Engine') else [])
    for p in sorted(package.rglob('*')):
        if p.is_file(): assert sha(p)==protected[str(RC)][p.relative_to(package).as_posix()]
    write(OUT/'protected_originals.json',protected)
    write(OUT/'bootstrap.json',dict(status='PASS',created_at=datetime.now().astimezone().isoformat(),release=RELEASE,
          source_files=len(records),source_bytes=sum(r['bytes'] for r in records),core_matches_accepted_archive=True,
          preexisting_document_differences=deltas,package=str(package),personal_saves_copied=False,git=False))
    print(json.dumps(dict(status='PASS',source_files=len(records),preexisting_differences=deltas,workspace=str(ROOT)),ensure_ascii=True),flush=True)

if __name__=='__main__': main()
