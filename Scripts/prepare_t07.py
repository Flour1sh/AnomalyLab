"""T07 offline preparation. Standard Python only; never imports Unreal or MCP.

T07 creates no gameplay assets. This inventories existing packages without
claiming that file existence or hashes validate Blueprint graphs or PIE.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = [
    'Core/Debug/BFL_PrototypeLog', 'Core/Types/EAnomalyOutcome',
    'Core/Types/EPrototypeRoundState', 'Interaction/BPI_Interactable',
    'Core/Components/BPC_Interaction', 'Core/Components/BPC_Wallet',
    'Core/Input/IA_Interact', 'Core/Input/IA_Restart', 'Core/Input/IMC_Prototype',
    'Anomalies/Containers/BP_AnomalyBox', 'Anomalies/Containers/BP_BoxSpawner',
    'Anomalies/Creatures/BP_Spider', 'Anomalies/Loot/BP_Loot_HighValue',
    'Anomalies/Loot/BP_Loot_Trash', 'UI/WBP_PrototypeHUD',
    'FirstPerson/Blueprints/BP_FirstPersonCharacter',
    'FirstPerson/Blueprints/BP_FirstPersonPlayerController',
    'FirstPerson/Blueprints/BP_FirstPersonGameMode', 'Prototype/Maps/L_Prototype',
]


def main():
    assets = []
    for package in PACKAGES:
        path = ROOT / 'Content' / (package + ('.umap' if package.endswith('/L_Prototype') else '.uasset'))
        data = path.read_bytes() if path.is_file() else b''
        assets.append(dict(package='/Game/' + package, file=path.relative_to(ROOT).as_posix(),
                           exists=path.is_file(), size=len(data),
                           sha256=hashlib.sha256(data).hexdigest() if data else None))
    state = (ROOT / 'Docs/STATE.md').read_text(encoding='utf-8-sig')
    config = (ROOT / 'Config/DefaultEngine.ini').read_text(encoding='utf-8-sig')
    checks = {
        'T06 recorded complete': 'Last Completed Ticket: T06' in state,
        'T07 current': 'Current Ticket: T07' in state,
        'required package files present and nonempty': all(a['exists'] and a['size'] for a in assets),
        'startup map': 'EditorStartupMap=/Game/Prototype/Maps/L_Prototype.L_Prototype' in config,
        'default map': 'GameDefaultMap=/Game/Prototype/Maps/L_Prototype.L_Prototype' in config,
    }
    report = dict(generated_utc=datetime.now(timezone.utc).isoformat(),
                  status='PASS' if all(checks.values()) else 'FAIL',
                  scope='Offline package presence and configuration only',
                  uassets_created=[], uassets_modified=[], compile='NOT RUN', PIE='NOT RUN',
                  T07_acceptance='PENDING', checks=checks, assets=assets)
    out = ROOT / 'Saved/T07'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'preparation.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"T07 offline preparation: {report['status']}; {len(assets)} packages; PIE NOT RUN")
    raise SystemExit(0 if all(checks.values()) else 1)


if __name__ == '__main__':
    main()
