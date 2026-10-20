"""Prepare T08 using standard Python. Does not launch UE, use MCP or edit assets.

T08 is user PIE acceptance and requires no new packages. File checks are not
Blueprint compilation, dependency validation, or gameplay acceptance.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from prepare_t07 import PACKAGES

ROOT = Path(__file__).resolve().parent.parent


def main():
    state = (ROOT / 'Docs/STATE.md').read_text(encoding='utf-8-sig')
    config = (ROOT / 'Config/DefaultEngine.ini').read_text(encoding='utf-8-sig')
    assets = []
    for package in PACKAGES:
        suffix = '.umap' if package == 'Prototype/Maps/L_Prototype' else '.uasset'
        path = ROOT / 'Content' / (package + suffix)
        data = path.read_bytes() if path.is_file() else b''
        assets.append({
            'package': '/Game/' + package,
            'file': path.relative_to(ROOT).as_posix(),
            'exists': path.is_file(),
            'size': len(data),
            'sha256': hashlib.sha256(data).hexdigest() if data else None,
        })
    checks = {
        'T07 recorded complete': 'Last Completed Ticket: T07' in state,
        'T08 current': 'Current Ticket: T08' in state,
        'required package files present and nonempty': all(a['size'] > 0 for a in assets),
        'startup map': 'EditorStartupMap=/Game/Prototype/Maps/L_Prototype.L_Prototype' in config,
        'default map': 'GameDefaultMap=/Game/Prototype/Maps/L_Prototype.L_Prototype' in config,
    }
    report = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'PASS' if all(checks.values()) else 'FAIL',
        'scope': 'Offline package presence, SHA-256 baseline and map configuration only',
        'uassets_required_to_create': [],
        'uassets_created': [], 'uassets_modified': [],
        'compile': 'NOT RUN', 'PIE': 'NOT RUN', 'T08_acceptance': 'PENDING USER',
        'checks': checks, 'assets': assets,
    }
    output = ROOT / 'Saved/T08'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'preparation.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"T08 offline preparation: {report['status']}; {len(assets)} packages; "
          '0 assets created/modified; compile and PIE NOT RUN; acceptance PENDING USER')
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
