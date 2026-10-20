"""Audit the final v0.2 source snapshot, package and six automated reports."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
run = json.loads((root / 'Saved/CppMigration/latest.json').read_text(encoding='utf-8'))
snapshot = Path(run['build_workspace'])
package = root / 'Builds/CppMigration' / Path(run['directory']).name / 'Windows'
reports = root / 'Saved/T18'
checks = []


def check(name, passed):
    checks.append({'check': name, 'passed': bool(passed)})


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


for target in ['editor', 'packaged']:
    for suite in ['stats', 'decision', 'flow']:
        path = reports / f'{target}_{suite}_report.json'
        data = json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else {}
        check(f'{target}/{suite} report PASS', data.get('status') == 'PASS'
              and data.get('checks') and all(c.get('passed') is True for c in data['checks']))
        check(f'{target}/{suite} checks present', len(data.get('checks', [])) >= {'stats': 50, 'decision': 40, 'flow': 60}[suite])

source_files = list((root / 'Source/AnomalyLab').rglob('*.cpp')) + list((root / 'Source/AnomalyLab').rglob('*.h'))
asset_files = [root / 'Content' / p for p in [
    'UI/WBP_PrototypeHUD.uasset', 'UI/WBP_ScanPanel.uasset', 'UI/WBP_HealthThreat.uasset',
    'UI/WBP_RoundDecision.uasset', 'Core/Components/BPC_Health.uasset',
    'FirstPerson/Blueprints/BP_FirstPersonCharacter.uasset',
    'Anomalies/Containers/BP_BoxSpawner.uasset', 'Anomalies/Creatures/BP_Spider.uasset']]
for source in source_files + asset_files:
    copied = snapshot / source.relative_to(root)
    check(f'Snapshot matches {source.relative_to(root)}', source.is_file() and copied.is_file() and sha(source) == sha(copied))

check('Independent EXE exists', (package / 'AnomalyLab.exe').is_file())
paks = package / 'AnomalyLab/Content/Paks'
check('Cooked IO Store exists', any(paks.glob('*.utoc')) and any(paks.glob('*.ucas')))
package_logs = sorted(Path(run['directory']).glob('package_*.log'))
successful = [p for p in package_logs if 'BUILD SUCCESSFUL' in p.read_text(encoding='utf-8', errors='replace')]
check('Final UAT build successful', bool(successful) and successful[-1] == package_logs[-1])
result = {'status': 'PASS' if all(c['passed'] for c in checks) else 'FAIL', 'checks': checks,
          'source_files': len(source_files), 'asset_files': len(asset_files),
          'package': str(package), 'package_log': str(package_logs[-1]) if package_logs else None,
          'scope': 'Source/selected assets and automated reports; no rendered visual or physical input audit'}
out = reports / 'final_audit.json'
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
assert result['status'] == 'PASS', [c['check'] for c in checks if not c['passed']]
print(json.dumps({'status': result['status'], 'checks': len(checks), 'package': str(package)}, ensure_ascii=False))
