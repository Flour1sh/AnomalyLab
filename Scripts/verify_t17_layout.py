"""Check stored widget geometry at the two v0.2 reference resolutions."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
data = json.loads((root / 'Saved/T17/inspection.json').read_text(encoding='utf-8'))
widgets = {w['name']: w for asset in data.values() for w in asset['widgets']}
names = ['MoneyText', 'HPText', 'ScanSummary', 'ScanHint', 'StatusText', 'DamageText', 'InteractionPrompt']
# ThreatText appears in the legacy HUD and health widget; inspect the latter explicitly.
health = next(w for w in data['/Game/UI/WBP_HealthThreat']['widgets'] if w['name'] == 'ThreatText')
legacy_threat = next(w for w in data['/Game/UI/WBP_PrototypeHUD']['widgets'] if w['name'] == 'ThreatText')
checks = []


def rect(w, width, height):
    ax, ay = w['anchor_min']
    x, y = w['position']
    sx, sy = w['size']
    # All v0.2 slots use fixed-point anchors. Read actual alignment from authoring contract.
    align = {'ScanSummary': (0., .5), 'ScanHint': (.5, 1.), 'StatusText': (.5, .5),
             'DamageText': (.5, .5), 'InteractionPrompt': (.5, .5), 'ThreatText': (.5, 0.)}
    u, v = align.get(w['name'], (0., 0.))
    left, top = ax * width + x - u * sx, ay * height + y - v * sy
    return left, top, left + sx, top + sy


def nonoverlap(a, b):
    return a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]


for width, height in [(1280, 720), (1920, 1080)]:
    for name in names:
        r = rect(widgets[name], width, height)
        checks.append({'check': f'{name} inside {width}x{height}',
                       'passed': r[0] >= 0 and r[1] >= 0 and r[2] <= width and r[3] <= height})
    top = [rect(widgets['MoneyText'], width, height), rect(legacy_threat, width, height),
           rect(widgets['HPText'], width, height), rect(health, width, height)]
    for i in range(len(top)):
        for j in range(i + 1, len(top)):
            checks.append({'check': f'Top HUD panels {i}/{j} separate at {width}x{height}',
                           'passed': nonoverlap(top[i], top[j])})
    checks.append({'check': f'Scan summary clear of upper HUD at {width}x{height}',
                   'passed': all(nonoverlap(rect(widgets['ScanSummary'], width, height), panel) for panel in top[:3])})

report = {'status': 'PASS' if all(x['passed'] for x in checks) else 'FAIL',
          'checks': checks, 'scope': 'Stored canvas rectangles only; no pixel or font raster inspection'}
out = root / 'Saved/T17/layout_report.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
assert report['status'] == 'PASS', [x['check'] for x in checks if not x['passed']]
print(f'T17 geometry PASS {len(checks)}/{len(checks)}')
