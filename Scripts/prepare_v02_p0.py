"""P0 source snapshot and hash verification. Does not modify Unreal assets."""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = ('Content', 'Config', 'Scripts', 'Docs', 'LowPolyLabPrototype',
           'LowPolyCharacterPrototype', 'Plugins', 'Source')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        out = args.verify.resolve()
        manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
        bad_backup, changed, missing = [], [], []
        for entry in manifest['files']:
            rel = entry['path']
            backup, source = out / 'source' / rel, ROOT / rel
            if not backup.is_file() or digest(backup) != entry['sha256']:
                bad_backup.append(rel)
            if not source.is_file():
                missing.append(rel)
            elif digest(source) != entry['sha256']:
                changed.append(rel)
        protected = [p for p in changed + missing if p.startswith(('Content/', 'Config/')) or p.endswith('.uproject')]
        existing = {e['path'] for e in manifest['files']}
        added = [p.relative_to(ROOT).as_posix() for folder in ('Content', 'Config')
                 for p in (ROOT / folder).rglob('*') if p.is_file() and p.relative_to(ROOT).as_posix() not in existing]
        report = dict(checked_utc=datetime.now(timezone.utc).isoformat(),
                      backup_status='PASS' if not bad_backup else 'FAIL',
                      protected_source_status='PASS' if not protected and not added else 'FAIL',
                      backup_failures=bad_backup, source_changed=changed, source_missing=missing,
                      protected_changes=protected, protected_additions=added,
                      file_count=len(manifest['files']))
        write(out / 'verification.json', report)
        print(json.dumps(report, ensure_ascii=False))
        return int(bool(bad_backup or protected or added))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT / 'Saved' / 'P0' / stamp
    (out / 'source').mkdir(parents=True, exist_ok=False)
    paths = list(ROOT.glob('*.uproject')) + list(ROOT.glob('*.md'))
    for folder in FOLDERS:
        paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts)
    for rel in ('Saved/T10/baseline.json', 'Saved/T06/baseline.json',
                'Saved/T06/protected_hashes.json', 'Saved/T06/callback_repair_hashes.json'):
        if (ROOT / rel).is_file():
            paths.append(ROOT / rel)
    manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(), source_root=str(ROOT),
                    snapshot_root=str(out / 'source'), scope=list(FOLDERS),
                    exclusions=['DerivedDataCache', 'Intermediate', 'Binaries', 'Builds',
                                'Saved except explicit historical validation manifests', '.codex', '__pycache__'],
                    files=[], status='IN_PROGRESS')
    for path in sorted(set(paths)):
        rel = path.relative_to(ROOT).as_posix()
        target = out / 'source' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        before = digest(path)
        shutil.copy2(path, target)
        if digest(target) != before or digest(path) != before:
            raise RuntimeError('Source changed or copy mismatch: ' + rel)
        manifest['files'].append(dict(path=rel, size=path.stat().st_size, sha256=before))
    manifest['status'] = 'PASS'
    manifest['total_bytes'] = sum(e['size'] for e in manifest['files'])
    write(out / 'manifest.json', manifest)
    write(ROOT / 'Saved/P0/latest.json', {'directory': str(out), 'manifest': str(out / 'manifest.json')})
    print(json.dumps({'status': 'PASS', 'directory': str(out), 'files': len(manifest['files']),
                      'bytes': manifest['total_bytes']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
