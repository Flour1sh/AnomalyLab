# T33 save audit and compatibility decision

## Existing real format

`UAnomalyMetaSaveGame::Meta` contains `FAnomalyMetaProgress`: SchemaVersion2, int64 Currency, BatteryLevel/PrecisionLevel/BackpackLevel/StoredDecoys, Revision, Extractions, TotalEarned, recent128 settlement/purchase GUIDs. `UAnomalyProgressionSubsystem` is GameInstance-scoped. Default slot `AnomalyLab_Meta_v04`. Actual path `FPaths::ProjectSavedDir()/SaveGames/<slot>.sav`, logged under `[MetaSave]`; packaged Saved may live under the package. Not guaranteed globally shared between different package folders.

Envelope: uint32 magic0x414C3034, envelope version1, payload length, CRC32, USaveGame payload; limit1MiB. Writes .tmp/readback, verified prior .bak via temporary backup, replace+verify, then memory changes. Schema1 accepted/sanitized to2, >2 blocks persistence and keeps bytes. In-memory purchases and settlements populated from saved recent IDs. StartedRuns only memory. No HP/carry/box/timer/scan count saved.

Important audited behavior: v0.4 invalid primary is preserved as `.bad.<guid>`, tries `.bak`, then falls back to zero/default if neither valid. This is not sufficient for v0.5's “cannot silently replace unreadable legacy progress” requirement; T35 must distinguish no-file from existing-unreadable and block financial writes with actionable feedback when both copies are invalid. Baseline tests retain original assertions; add separate v0.5 corruption expectations.

## Minimal migration (planned, T35)

- Retain class paths, all fields, Schema2 and default slot name; existing economic format needs no new field for value-only GameInstance transition/result. No rename to a v05 slot that hides existing assets. Any later durable field addition must justify schema/version migration in this file first.
- Keep persistent account transactions authoritative in the existing subsystem. Hub launch consumes stored decoy ONCE before travel; Lab initialization must claim copied decoy count and never consume again. Quit/death/technical travel failure do not refund a consumed decoy, matching v0.4's launch/quit semantics. Permanent upgrades remain.
- New working copy and new package directory have different Saved directories. Copying source does NOT migrate a player's save. T33 deliberately copies no personal SaveGames. T35/T42 must test explicit legacy import: user selects/identifies old valid .sav/.bak, validate in isolation, show detected balance/upgrades, create backup in new location, install validated bytes through the persistence layer without altering old file. A same-location upgrade simply reads current slot. Do not search arbitrary drives or hardcode developer F: paths into the shipped game.
- Existing file unreadable/future → do not write zero/default over it. Report error and allow restore/import/new-game selection separately; starting fresh requires explicit choice and preserves original bytes. No-file → legitimate new zero account. Old valid backup recovery stays supported and visible.
- No resumed Lab on startup. Menu continue → Hub with durable meta. Crash after launch means unextracted loot is lost. Crash after successful durable credit means balance already increased exactly once; showing/reloading a result must not credit it again. New gameplay has no pointer persistence or replay transaction.
- Report DTO can remain GameInstance-only; restart may display “上次探索已中断” instead of restoring a live run. Telemetry/journal (T41) separate from economic authority.

## Required experiments

Original v0.4 `run_t29.py`: boundaries, purchase write/read across OS processes, quit write/read, Schema1 migration write/read, future write/read, extraction write failure (10 processes). Preserve all as baseline.

T35 additions: representative valid Schema2 fixture with nonzero currency/all levels/decoy/revision/GUIDs; old→new path import byte/hash/field equality; same-path continuation; duplicate launch claim/settlement; launch crash/restart; commit-before-Hub crash/restart; corrupt primary+valid backup; both corrupt blocked; future bytes unchanged; copy/import failure leaves both old/new untouched; death-vs-extraction frame and repeat E; three sequential Hub↔Lab returns. Test slots always unique Automation_, no default player slot cleanup.

Rollback: restore the task's whole Project checkpoint into a NEW directory, rebuild with a new ASCII build context. Back up player saves separately before manual migration; checkpoints/release archives exclude personal saves. Old RC/old player files remain usable and unchanged.

## T35 implemented boundary
Schema2 and default slot retained. Existing unreadable primary+backup blocks Progression.Commit and launch; Load preserves diagnostic bad copy and original bytes. Explicit startup -AnomalyImportSave=<absolute sav/bak path> calls the same private ImportSave implementation covered by native isolated fixture tests: source Decode only (no Load that could write .bad), sanitize Schema1→2, target must have neither primary nor backup, durable write/readback then memory. Repeated import refuses overwrite. Source never modified. No actual player old save has been imported by Agent. Restart returns Hub with permanent account and no carry/result replay. Actual execution outcomes are in T35_REPORT and Saved/V05/T35.
