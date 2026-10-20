"""Recoverable v0.4 snapshots; accepted v0.3 archive is read-only."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Saved/V04'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def verify(snapshot):
    records = json.loads((snapshot/'manifest.json').read_text(encoding='utf-8'))['files']
    failures = [r['path'] for r in records if not (snapshot/'Project'/r['path']).is_file()
                or sha(snapshot/'Project'/r['path']) != r['sha256']]
    result = dict(status='FAIL' if failures else 'PASS', files=len(records), failures=failures,
                  snapshot=str(snapshot), checked_at=datetime.now().astimezone().isoformat())
    write(OUT/'checkpoint_verification.json', result)
    assert not failures, result
    return result

def create(label):
    assert label.replace('-', '').replace('_', '').isalnum()
    snapshot = OUT/('Checkpoint_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+label)
    snapshot.mkdir(parents=True, exist_ok=False)
    files = []
    for folder in ('Source','Config','Content','Scripts','Docs','Binaries/Win64'):
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    files.extend(p for p in ROOT.iterdir() if p.suffix in ('.md','.uproject') and p.is_file())
    records = []
    for source in sorted(files):
        relative = source.relative_to(ROOT)
        target = snapshot/'Project'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = sha(source)
        shutil.copy2(source, target)
        assert sha(target) == digest and sha(source) == digest, relative
        records.append(dict(path=relative.as_posix(), sha256=digest, bytes=source.stat().st_size))
    write(snapshot/'manifest.json', dict(label=label, created_at=datetime.now().astimezone().isoformat(), files=records))
    (snapshot/'README_RESTORE.md').write_text(
        '# v0.4 recovery point\n\nCopy Project into a NEW working directory. Do not overlay an older snapshot on a later checkout: new C++ files/assets would remain.\n'
        'This includes Source, Config, Content, Scripts, Docs, uproject and Editor binaries. Rebuild Editor through the ASCII workspace before opening a relocated copy.\n'
        'Use the unchanged accepted v0.3 Project archive for original model/audio sources. Builds and test evidence remain in the main project; this snapshot is not a release.\n'
        'Verify: python Scripts/checkpoint_v04.py --verify <snapshot>\n', encoding='utf-8')
    result = verify(snapshot)
    write(OUT/('checkpoint_'+label+'.json'), result)
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--label')
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.verify.resolve()) if args.verify else create(args.label), ensure_ascii=True))
