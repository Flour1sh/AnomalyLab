"""Archive final evidence and verify the reviewed source/package snapshot and PNG sizes."""
import hashlib
import json
import shutil
import struct
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = root / 'Saved/T19Menu'
checks = []


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def check(name, passed):
    checks.append(dict(check=name, passed=bool(passed)))
    assert passed, name


package = read(out / 'package_report.json')
check('Final UAT completed', package['status'] == 'PASS' and Path(package['exe']).is_file())
manifest = read(Path(package['source_manifest']))
work = Path(read(root / 'Saved/CppMigration/latest.json')['build_workspace'])
for relative, digest in manifest.items():
    check('Source and build snapshot: ' + relative,
          hashlib.sha256((root / relative).read_bytes()).hexdigest() == digest == hashlib.sha256((work / relative).read_bytes()).hexdigest())
reload = read(out / 'reload_report.json')
check('Asset reload passed', reload['status'] == 'PASS' and all(item['passed'] for item in reload['checks']))
rendered = []
for width, height in ((1280, 720), (1920, 1080)):
    evidence = read(out / f'latest_{width}x{height}.json')
    check(f'Final packaged menu {width}x{height}', evidence['status'] == 'PASS' and evidence['target'] == 'packaged' and evidence['checks'] == 21)
    directory = Path(evidence['directory'])
    for name in ('01_main_menu', '02_settings', '03_field_guide', '04_quit_confirmation', '04b_loading', '05_level01'):
        data = (directory / (name + '.png')).read_bytes()
        check(f'Rendered PNG {name} {width}x{height}', data[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', data[16:24]) == (width, height))
    rendered.append(evidence)
for suite, count in (('decision', 47), ('flow', 66)):
    original = root / f'Saved/T18/editor_{suite}_report.json'
    regression = read(original)
    check('v0.2 Editor regression: ' + suite, regression['status'] == 'PASS' and len(regression['checks']) == count and all(item['passed'] for item in regression['checks']))
    shutil.copy2(original, out / f'v02_editor_{suite}_report.json')
summary = dict(status='PASS_AUTOMATED_PENDING_MANUAL', checks=checks, package=package, rendered=rendered,
               physical_input='PENDING_MANUAL', settings_apply_and_persistence='PENDING_MANUAL', audio_listening='PENDING_MANUAL',
               visual_review='Agent inspected real rendered main/settings/loading/Level01 PNGs; not human gameplay acceptance')
(out / 'delivery_audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(dict(status=summary['status'], checks=len(checks), exe=package['exe']), ensure_ascii=True))
