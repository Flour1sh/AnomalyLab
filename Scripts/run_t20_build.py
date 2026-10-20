"""Reproducible T20 build only. No gameplay, packaging, MCP calls or UI control."""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Saved/T20'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--step', choices=('all', 'cpp', 'assets', 'reload'), default='all')
args = parser.parse_args()
OUT.mkdir(parents=True, exist_ok=True)
stamp = datetime.now().strftime('%Y%m%dT%H%M%S%f')
events = []
for step, command, report in (
        ('cpp', ['build-editor'], None),
        ('assets', ['editor', '--script', 'build_t20_assets.py', '--phase', 't20-build'], 'build_report.json'),
        ('reload', ['editor', '--script', 'verify_t20_assets.py', '--phase', 't20-reload'], 'reload_report.json')):
    if args.step not in ('all', step):
        continue
    start = time.time()
    full = [sys.executable, str(ROOT / 'Scripts/cpp_migration.py'), *command]
    print('T20 ' + step, flush=True)
    result = subprocess.run(full, cwd=ROOT, env=dict(os.environ, PYTHONUTF8='1'))
    assert result.returncode == 0, f'{step} failed; inspect Saved/CppMigration logs'
    entry = dict(step=step, command=full, exit_code=result.returncode)
    if report:
        path = OUT / report
        assert path.is_file() and path.stat().st_mtime >= start, f'{step}: no fresh report'
        content = json.loads(path.read_text(encoding='utf-8'))
        assert content['status'] in ('BUILT', 'PASS'), content
        entry['report'] = str(path)
    events.append(entry)
(OUT / ('build_driver_' + stamp + '.json')).write_text(json.dumps(dict(status='PASS', steps=events,
    gameplay_tested=False), ensure_ascii=False, indent=2), encoding='utf-8')
