"""Full v0.5 task snapshots and read-only protection audits."""
import argparse, hashlib, json, shutil
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Saved/V05'
FOLDERS=('Source','Config','Content','Scripts','Docs','Binaries/Win64','LowPolyLabPrototype','LowPolyCharacterPrototype','T11EAssets','GameAudio','MenuAudio','ScenePolishAssets')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def files(root):
    for folder in FOLDERS:
        for p in sorted((root/folder).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts: yield p
    for p in sorted(root.iterdir()):
        if p.is_file() and p.suffix in ('.md','.uproject'): yield p
def protected(task='T33'):
    records=json.loads((OUT/'T33/protected_originals.json').read_text(encoding='utf-8')); results=[]
    for root,expected in records.items():
        base=Path(root); actual={p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob('*')) if p.is_file()}
        changed=sorted(p for p in expected.keys()|actual.keys() if expected.get(p)!=actual.get(p))
        results.append(dict(root=root,files=len(expected),status='FAIL' if changed else 'PASS',changed=changed))
    manifest=json.loads((OUT/'T33/source_copy_manifest.json').read_text(encoding='utf-8'))
    expected={r['path']:r['sha256'] for r in manifest['files']}; base=Path(manifest['original'])
    actual={p.relative_to(base).as_posix():sha(p) for p in files(base)}
    changed=sorted(p for p in expected.keys()|actual.keys() if expected.get(p)!=actual.get(p))
    external=OUT/'T35/external_baseline_document_changes.json'
    documented={}
    if task not in ('T33','T34') and external.exists():
        documented={r['path']:r['observed_sha256'] for r in json.loads(external.read_text(encoding='utf-8'))['records']}
        assert set(documented)=={'Docs/STATE.md','Docs/v0.4/FINAL_REPORT.md','Docs/v0.4/T32_REPORT.md','Docs/v0.4/progress.md'}
    accepted_external=bool(changed) and set(changed)==set(documented) and all(actual.get(p)==h for p,h in documented.items())
    results.append(dict(root=str(base),files=len(expected),status='PASS_WITH_EXTERNAL_DOCS' if accepted_external else 'FAIL' if changed else 'PASS',changed=changed,original_byte_identity=not changed,external_evidence=str(external) if accepted_external else None))
    result=dict(status='PASS' if all(r['status'] in ('PASS','PASS_WITH_EXTERNAL_DOCS') for r in results) else 'FAIL',results=results,checked_at=datetime.now().astimezone().isoformat(),scope='Full payload/inventory SHA; exactly pinned external maintenance documentation changes retained separately; no writes to originals')
    write(OUT/task/'protected_after.json',result); assert result['status']=='PASS',result
    return result
def verify(snapshot):
    assert snapshot.resolve().is_relative_to(OUT.resolve()),'Only v0.5 checkpoints'
    expected=json.loads((snapshot/'manifest.json').read_text(encoding='utf-8'))['files']
    bad=[r['path'] for r in expected if not (snapshot/'Project'/r['path']).is_file() or sha(snapshot/'Project'/r['path'])!=r['sha256']]
    actual={p.relative_to(snapshot/'Project').as_posix() for p in (snapshot/'Project').rglob('*') if p.is_file()}
    bad+=sorted(actual-{r['path'] for r in expected})
    result=dict(status='FAIL' if bad else 'PASS',files=len(expected),snapshot=str(snapshot),failures=bad,checked_at=datetime.now().astimezone().isoformat())
    write(OUT/'checkpoint_verification.json',result); assert not bad,result
    return result
def create(label,task='T33'):
    assert label.replace('_','').isalnum()
    dest=OUT/('Checkpoint_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+label)
    dest.mkdir(parents=True,exist_ok=False); records=[]
    for src in files(ROOT):
        rel=src.relative_to(ROOT); dst=dest/'Project'/rel; digest=sha(src)
        dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
        assert sha(dst)==digest and sha(src)==digest,str(rel)
        records.append(dict(path=rel.as_posix(),sha256=digest,bytes=src.stat().st_size))
    write(dest/'manifest.json',dict(label=label,created_at=datetime.now().astimezone().isoformat(),files=records))
    (dest/'README_RESTORE.md').write_text('# v0.5 task recovery\n\nRestore Project into a NEW directory, never overlay. Source/Config/Content/Scripts/Docs, Editor binaries, original model/audio sources included. Personal SaveGames, caches, test package and runtime evidence excluded; evidence stays in original Saved/V05 and legacy runner output folders.\n\nVerify with checkpoint_v05.py --verify <snapshot> from this workspace. Relocated build: create NEW Saved/CppMigration/<id>, write Saved/CppMigration/latest.json with absolute directory and NEW ASCII build_workspace inside Saved/BuildWork, check ENGINE, close UE then python Scripts/cpp_migration.py build-editor. Do not use original v0.4 context or old prepare.\n\nThis task never writes original v0.4 code/assets/RC/archives. Four externally maintained original Docs changes have pinned SHA evidence in Saved/V05/T35/external_baseline_document_changes.json; strict original identity FAIL is retained. Same-disk checkpoint is not offsite backup. Task checkpoints are not packaged game releases.\n',encoding='utf-8')
    result=verify(dest); write(OUT/('checkpoint_'+label+'.json'),result)
    if task=='T33':baseline=json.loads((OUT/'T33/source_copy_manifest.json').read_text(encoding='utf-8'))
    else:
        base=json.loads((OUT/'checkpoint_T33_verified.json').read_text(encoding='utf-8'))
        baseline=json.loads((Path(base['snapshot'])/'manifest.json').read_text(encoding='utf-8'))
    old={r['path']:r['sha256'] for r in baseline['files']}; new={r['path']:r['sha256'] for r in records}
    write(OUT/task/'changed_files.json',dict(added=sorted(new.keys()-old.keys()),deleted=sorted(old.keys()-new.keys()),modified=sorted(p for p in old.keys()&new.keys() if old[p]!=new[p])))
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--task',default='T33',choices=['T33','T34','T35','T36','T37','T38','T39','T40','T41','T42']);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--label');g.add_argument('--verify',type=Path);g.add_argument('--audit-protected',action='store_true');a=p.parse_args()
    print(json.dumps(protected(a.task) if a.audit_protected else verify(a.verify.resolve()) if a.verify else create(a.label,a.task),ensure_ascii=True),flush=True)
