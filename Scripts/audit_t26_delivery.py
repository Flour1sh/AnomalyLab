"""Read-only accepted archive verification and T26 scope/package/telemetry audit."""
import argparse,hashlib,json,re
from datetime import datetime
from pathlib import Path
from checkpoint_v04 import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Saved/V04/T26'
p=argparse.ArgumentParser();p.add_argument('--runtime',type=Path,required=True);args=p.parse_args()
checks=[]
def check(name,value):
    checks.append(dict(check=name,passed=bool(value)))
    if not value: print('FAIL: '+name,flush=True)
archive=ROOT/'Saved/Releases/v0.3_ScenePolish_Accepted_20261011'
manifest=json.loads((archive/'release_manifest.json').read_text(encoding='utf-8'))
failures=[r['path'] for r in manifest['files'] if not (archive/r['path']).is_file() or sha(archive/r['path'])!=r['sha256']]
check('Accepted v0.3 archived manifest files unchanged (read-only)',not failures)
baseline=json.loads((ROOT/'Saved/V04/checkpoint_initialization.json').read_text(encoding='utf-8'))
snapshot=Path(baseline['snapshot'])
before=json.loads((snapshot/'manifest.json').read_text(encoding='utf-8'))['files']
before_hashes={r['path']:r['sha256'] for r in before}
original=[r for r in manifest['files'] if r['path'].startswith(('Project/Source/','Project/Config/','Project/Content/'))]
check('Initialization Source/Config/Content exactly matches accepted v0.3',all(before_hashes.get(r['path'][8:])==r['sha256'] for r in original))
changed=[name for name,digest in before_hashes.items() if not (ROOT/name).is_file() or sha(ROOT/name)!=digest]
existing=set(before_hashes)
added=[q.relative_to(ROOT).as_posix() for f in ('Source','Config','Content','Scripts','Docs')
       for q in (ROOT/f).rglob('*') if q.is_file() and '__pycache__' not in q.parts and q.relative_to(ROOT).as_posix() not in existing]
content_changes=[name for name in changed+added if name.startswith('Content/')]
allowed=json.loads((OUT/'assets.json').read_text(encoding='utf-8'))
check('Content modifications restricted to three regions, exploration map and HUD',set(content_changes)==set(allowed['mutable']))
check('No Config changes',not any(n.startswith('Config/') for n in changed+added))
check('All 1070 non-target Content hashes still unchanged',all(sha(ROOT/name)==digest for name,digest in allowed['protected_sha256'].items()))
package=json.loads((OUT/'package_report.json').read_text(encoding='utf-8'))
source=json.loads(Path(package['source_manifest']).read_text(encoding='utf-8'))
work=json.loads((ROOT/'Saved/CppMigration/latest.json').read_text(encoding='utf-8'))['build_workspace']
check('Package sources still match current and ASCII build workspace',all(sha(ROOT/name)==digest and sha(Path(work)/name)==digest for name,digest in source.items()))
windows=Path(package['directory'])/'Windows'
files=[q for q in windows.rglob('*') if q.is_file()]
check('Full packaged directory includes EXE and cooked containers',Path(package['exe']).is_file() and any(q.suffix=='.utoc' for q in files) and any(q.suffix=='.ucas' for q in files))
package_hashes={q.relative_to(windows).as_posix():sha(q) for q in files if not any(part in ('Saved','Intermediate') for part in q.relative_to(windows).parts)}
(OUT/'package_sha256.json').write_text(json.dumps(package_hashes,ensure_ascii=False,indent=2),encoding='utf-8')
text=args.runtime.read_text(encoding='utf-8',errors='replace')
events=re.findall(r'\[Region\] id=(\w+) round=(\d+) event=(\w+) open_count=(\d+) scan_count=(\d+) reward=(\d+) threat=(\d+) survive=(\d+)',text)
check('Live core flow logs every required regional telemetry event (FName case-insensitive)',set(e[2].lower() for e in events)>={'open','scan','reward','threat','survive'})
check('Live telemetry is grouped by all three regions',set(e[0] for e in events)=={'A','B','C'})
result=dict(status='PASS' if all(c['passed'] for c in checks) else 'FAIL',checked_at=datetime.now().astimezone().isoformat(),
    checks=checks,archive_files=len(manifest['files']),archive_failures=failures,baseline_files=len(original),
    changed=changed,added=added,package_hash_files=len(package_hashes),telemetry_events=len(events),runtime=str(args.runtime),
    scope='Read-only audit. Original v0.3 derived verification_report timestamp was updated during initialization; manifest files remain unchanged.')
(OUT/'delivery_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('changed','added','checks')},ensure_ascii=True))
assert result['status']=='PASS'
